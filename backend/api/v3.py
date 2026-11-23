import json
import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, File, Form, Header, Query, Response, UploadFile
from backend.api.tasks import require_prediction
from backend.db import store
from backend.schemas.v3 import (Calibration,DatasetRequest,Decision,Evaluation,Replay,ReviewStart,
                                Reviewer,RunStart,Sheet)
from backend.services import benchmark, datasets, physical, providers, review
from backend.services.common import Problem, canonical, consume, digest, event, one, rows

router=APIRouter()


def token_valid(value, env):
    expected=os.getenv(env,"")
    return bool(expected and value and secrets.compare_digest(value.encode(),expected.encode()))


def operator(authorization: str=Header("")):
    if not authorization.startswith("Bearer ") or not token_valid(authorization[7:],"MS_OPERATOR_TOKEN"):
        raise Problem(403,"Operator access required")


admin=[Depends(operator)]


def zipped(content, name):
    return Response(content,media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="{name}.zip"',
                                                                 "Cache-Control":"private, no-store"})


@router.post("/api/dataset/generate",dependencies=admin,tags=["datasets"])
def create_dataset(body:DatasetRequest):
    return datasets.build(**body.model_dump())


@router.get("/api/dataset/export",tags=["datasets"])
def export_dataset(dataset_id:str):
    return zipped(datasets.export(dataset_id),dataset_id)


@router.get("/api/v1/datasets/{dataset_id}/cases",dependencies=admin,tags=["datasets"])
def case_list(dataset_id:str):
    one("SELECT id FROM datasets WHERE id=?",(dataset_id,))
    return rows("SELECT id AS task_id,kind,pair,layout,difficulty FROM cases WHERE dataset=? ORDER BY position",(dataset_id,))


@router.post("/api/v1/benchmark/runs",dependencies=admin,tags=["benchmarks"])
def start_run(body:RunStart):
    return benchmark.start(body.dataset_id,body.provider,body.model,body.mode,body.max_output_tokens)


@router.post("/api/v1/benchmark/runs/{run_id}/step",dependencies=admin,tags=["benchmarks"])
def advance(run_id:str,count:int=Query(1,ge=1,le=10)):
    return benchmark.step(run_id,count)


@router.get("/api/v1/benchmark/runs/{run_id}",dependencies=admin,tags=["benchmarks"])
def run_status(run_id:str):
    return benchmark.score(run_id)


@router.get("/api/v1/benchmark/runs/{run_id}/export",dependencies=admin,tags=["benchmarks"])
def private_run(run_id:str):
    return benchmark.export_run(run_id)


@router.post("/api/v1/benchmark/replay",dependencies=admin,tags=["benchmarks"])
def import_run(body:Replay):
    return benchmark.replay(body.model_dump())


@router.get("/api/benchmark/results",tags=["benchmarks"])
def results():
    return benchmark.results()


@router.get("/api/v1/judge/models",tags=["judge"])
def judge_models():
    return {"models":providers.models("openrouter")}


@router.post("/api/tasks/{task_id}/evaluate",tags=["judge"])
def evaluate(task_id:str,body:Evaluation,ms_session:str|None=Cookie(None),x_judge_code:str=Header("")):
    if not token_valid(x_judge_code,"MS_JUDGE_CODE"):
        raise Problem(403,"Judge access required")
    require_prediction(task_id,ms_session)
    providers.ready("openrouter",body.model)
    with store.database() as db:
        db.execute("BEGIN IMMEDIATE")
        old=db.execute("SELECT status FROM evaluations WHERE task=? AND session=? AND model=?",
                       (task_id,ms_session,body.model)).fetchone()
        if old:
            return {"task_id":task_id,"status":old[0]}
        consume(db,"judge-global",int(os.getenv("MS_JUDGE_CALL_CAP","0")))
        consume(db,"judge-"+digest(ms_session),int(os.getenv("MS_SESSION_CALL_CAP","5")))
        db.execute("INSERT INTO evaluations(task,session,model,status,metadata) VALUES(?,?,?,'sending','{}')",
                   (task_id,ms_session,body.model))
    task=store.metadata(task_id)
    outcome,raw,parsed,meta=providers.infer("openrouter",body.model,"vision",task["question"],task["options"],
                                          store.image_bytes(task_id),512)
    status="failed" if outcome=="error" else "recorded"
    with store.database() as db:
        db.execute("UPDATE evaluations SET status=?,raw=?,metadata=? WHERE task=? AND session=? AND model=?",
                   (status,raw,canonical({**meta,"parsed":parsed}),task_id,ms_session,body.model))
    return {"task_id":task_id,"status":status}


@router.post("/api/v1/reviews",dependencies=admin,tags=["blind review"])
def make_review(body:ReviewStart):
    return review.create(body.dataset_id,body.count)


@router.get("/api/v1/reviews/{rid}/packets/{reviewer}",dependencies=admin,tags=["blind review"])
def review_packet(rid:str,reviewer:Reviewer):
    return zipped(review.packet(rid,reviewer),reviewer)


@router.post("/api/v1/reviews/{rid}/sheets/{reviewer}",dependencies=admin,tags=["blind review"])
def review_sheet(rid:str,reviewer:Reviewer,body:Sheet):
    return review.submit(rid,reviewer,[r.model_dump() for r in body.responses])


@router.get("/api/v1/reviews/{rid}",dependencies=admin,tags=["blind review"])
def review_results(rid:str):
    return review.report(rid,detail=True)


@router.post("/api/v1/reviews/{rid}/decision",dependencies=admin,tags=["blind review"])
def decide(rid:str,body:Decision):
    return review.adjudicate(rid,body.accepted,body.notes)


@router.get("/api/v1/validation/tasks/{taskId}/fixture",dependencies=admin,tags=["physical validation"])
def fixture(taskId:str):
    return zipped(physical.fixture(taskId),"fixture")


@router.post("/api/v1/validation/calibration",dependencies=admin,tags=["physical validation"])
def calibration(body:Calibration):
    return physical.calibrate(body.task_id,body.model_dump())


@router.post("/api/v1/validation/tasks/{taskId}/observations",dependencies=admin,tags=["physical validation"])
def observation(taskId:str,stage:Annotated[str,Form(max_length=20)],observer:Annotated[str,Form(max_length=100)],
                observed:Annotated[str,Form(max_length=3)],calibration_sha256:Annotated[str,Form(max_length=64)],
                capture:Annotated[UploadFile,File()]):
    try:
        raw=capture.file.read(8*1024*1024+1)
        return physical.capture(taskId,calibration_sha256,stage,observer,observed,raw)
    finally:
        capture.file.close()


@router.get("/api/v1/validation/tasks/{taskId}",tags=["physical validation"])
def validation_task(taskId:str):
    return physical.status(taskId)


@router.get("/api/v1/validation/status",tags=["physical validation"])
def validation_status():
    reports=[review.report(r["id"]) for r in rows("SELECT id FROM reviews")]
    return {"synthetic":{"dataset_cases":one("SELECT count(*) AS n FROM cases")["n"]},
            "blind_review":{"packets":len(reports),"sealed_sheets":sum(x["sealed_sheets"] for x in reports)},
            "physical":physical.summary()}


@router.get("/api/v1/validation/report",tags=["physical validation"])
def validation_report(dataset_id:str):
    d=one("SELECT digest,suite FROM datasets WHERE id=?",(dataset_id,))
    r=rows("SELECT id FROM reviews WHERE dataset=?",(dataset_id,))
    return {"dataset_id":dataset_id,"manifest_sha256":d["digest"],"suite":d["suite"],
            "synthetic":{"verified_cases":one("SELECT count(*) AS n FROM cases WHERE dataset=?",(dataset_id,))["n"]},
            "blind_review":review.report(r[0]["id"]) if r else {"state":"pending","sealed_sheets":0},
            "physical":physical.summary(dataset_id)}

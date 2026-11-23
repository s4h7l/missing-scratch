from fastapi import APIRouter, Query, Response
from backend.api.v3 import admin
from backend.db.store import database
from backend.services.common import Problem, archive, canonical, digest, event, one, rows
from backend.services import benchmark, datasets

router=APIRouter()


@router.get("/api/v1/benchmark/runs/{rid}/pairs/{pair}",dependencies=admin,tags=["benchmarks"])
def diagnostic(rid:str,pair:str):
    run=one("SELECT dataset FROM runs WHERE id=?",(rid,))
    cases=rows("SELECT id,kind,answer,evidence,png,digest FROM cases WHERE dataset=? AND pair=? ORDER BY position",
               (run["dataset"],pair))
    if not cases:
        raise Problem(404,"Unknown pair in this run")
    records={r["task_id"]:r for r in benchmark.export_run(rid)["records"]}
    import json
    files=[]; summary=[]
    for c in cases:
        files.append((c["id"]+".png",c["png"]))
        summary.append({"task_id":c["id"],"answer":c["answer"],"evidence":json.loads(c["evidence"]),
                        "record":records.get(c["id"]),"input_sha256":c["digest"]})
    files.append(("pair.json",canonical(summary)))
    return Response(archive(files),media_type="application/zip",headers={"Cache-Control":"no-store"})


@router.get("/api/v1/validation/tasks/{cid}/history",dependencies=admin,tags=["physical validation"])
def history(cid:str):
    return rows("""SELECT k.id AS calibration_sha256,k.created,k.record,c.stage,c.observed,c.observer,
        c.digest AS sanitized_sha256,c.original_digest AS original_sha256,c.created AS captured_at
        FROM calibrations k LEFT JOIN captures c ON c.cal=k.id WHERE k.task=? ORDER BY k.rowid,c.stage""",(cid,))


@router.get("/api/v1/validation/captures/{sha}/original",dependencies=admin,tags=["physical validation"])
def original(sha:str):
    r=one("SELECT original,original_digest FROM captures WHERE digest=?",(sha,))
    if digest(r["original"])!=r["original_digest"]:
        raise Problem(409,"Capture integrity mismatch")
    return Response(r["original"],media_type="application/octet-stream",headers={"Cache-Control":"no-store"})


@router.post("/api/v1/validation/captures/{sha}/approve",dependencies=admin,tags=["physical validation"])
def approve(sha:str,consent_confirmed:bool=Query(...)):
    if not consent_confirmed:
        raise Problem(422,"Confirm permission to show this sanitized frame to judges")
    one("SELECT digest FROM captures WHERE digest=?",(sha,))
    with database() as db:
        db.execute("INSERT OR IGNORE INTO approved_media(digest) VALUES(?)",(sha,))
        event(db,"media.approved",sha,sha)
    return {"url":"/api/v1/validation/media/"+sha}


@router.get("/api/v1/validation/media/{sha}",tags=["physical validation"])
def approved(sha:str):
    r=one("SELECT png FROM captures JOIN approved_media USING(digest) WHERE digest=?",(sha,))
    if digest(r["png"])!=sha:
        raise Problem(409,"Capture integrity mismatch")
    return Response(r["png"],media_type="image/png",headers={"Cache-Control":"no-store"})

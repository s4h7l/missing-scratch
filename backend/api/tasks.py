from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Cookie, HTTPException, Response

from backend.core.factory import GenerationExhausted, generate_pair
from backend.db import store
from backend.schemas.tasks import GenerateRequest, PredictRequest, PredictResponse, PublicPair, PublicTask, RevealResponse
from backend.services.task_service import prepare
from backend.services import sessions
import json

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
SESSION_COOKIE = "ms_session"
PRIVATE = {"Cache-Control": "private, no-store", "Vary": "Cookie"}


def ensure_session(response: Response, session_id: str | None) -> str:
    if not sessions.active(session_id):
        session_id = sessions.issue()
        response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax",
                            secure=os.getenv("MISSING_SCRATCH_COOKIE_SECURE") == "1",
                            max_age=8*60*60, path="/")
    return session_id


def new_tasks(body: GenerateRequest, pair_id: str | None) -> list[dict]:
    try:
        pair = generate_pair(body.kind)
    except GenerationExhausted as exc:
        raise HTTPException(503, "Could not generate a verified layout. Retry.") from exc
    records = [prepare(task, pair_id) for task in (pair if pair_id else pair[:1])]
    store.save_batch(records)
    return [record[0] for record in records]


def public_task(task_id: str):
    task = store.metadata(task_id)
    if task is None:
        raise HTTPException(404, "Unknown task")
    return task


@router.post("/generate", response_model=PublicTask)
def generate(body: GenerateRequest, response: Response, ms_session: str | None = Cookie(None)):
    task, = new_tasks(body, None)
    ensure_session(response, ms_session)
    return task


@router.post("/generate-pair", response_model=PublicPair)
def generate_task_pair(body: GenerateRequest, response: Response, ms_session: str | None = Cookie(None)):
    pair_id = "P-" + secrets.token_hex(12)
    tasks = new_tasks(body, pair_id)
    ensure_session(response, ms_session)
    return {"pair_id": pair_id, "tasks": tasks}


@router.get("/{task_id}", response_model=PublicTask)
def get_public_task(task_id: str):
    return public_task(task_id)


PNG = {200: {"content": {"image/png": {}}}}


@router.get("/{task_id}/image", response_class=Response, responses=PNG)
def get_task_image(task_id: str):
    image = store.image_bytes(task_id)
    if image is None:
        raise HTTPException(404, "Task image unavailable")
    return Response(image, media_type="image/png")


@router.post("/{task_id}/predict", response_model=PredictResponse)
def predict(task_id: str, body: PredictRequest, response: Response, ms_session: str | None = Cookie(None)):
    public = public_task(task_id)
    if body.prediction not in public["options"]:
        raise HTTPException(422, "Choose one of the displayed options")
    session = ensure_session(response, ms_session)
    if not store.save_prediction(session, task_id, body.prediction):
        raise HTTPException(409, "Prediction is locked for this task")
    return {"task_id": task_id, "status": "recorded"}


def require_prediction(task_id, session_id):
    task = public_task(task_id)
    prediction = store.locked_prediction(session_id, task_id, task["pair_id"]) if sessions.active(session_id) else None
    if prediction is None:
        message = "Record both predictions before reveal" if task["pair_id"] else "Record a prediction before reveal"
        raise HTTPException(403, message, headers=PRIVATE)
    return prediction


@router.get("/{task_id}/reveal", response_model=RevealResponse)
def reveal(task_id: str, response: Response, ms_session: str | None = Cookie(None)):
    prediction = require_prediction(task_id, ms_session)
    private = store.metadata(task_id, private=True)
    evidence = private.get("evidence")
    if evidence is None:  # Previously generated visibility tasks.
        evidence = {"solver_checks": private["checks"], "scene": private["scene"]}
    with store.database() as db:
        evaluations=db.execute("SELECT model,status,raw,metadata FROM evaluations WHERE task=? AND session=?",
                               (task_id,ms_session)).fetchall()
    evidence["model_evaluations"]=[{"model":r["model"],"status":r["status"],"reply":r["raw"],
                                     "parsed":json.loads(r["metadata"]).get("parsed")} for r in evaluations]
    response.headers.update(PRIVATE)
    return {"task_id": task_id, "prediction": prediction, "ground_truth": private["answer"],
            "correct": prediction == private["answer"], "evidence": evidence}


@router.get("/{task_id}/reveal/image", response_class=Response, responses=PNG)
def reveal_image(task_id: str, ms_session: str | None = Cookie(None)):
    require_prediction(task_id, ms_session)
    image = store.image_bytes(task_id, reveal=True)
    if image is None:
        raise HTTPException(404, "No reveal image for this task", headers=PRIVATE)
    return Response(image, media_type="image/png", headers=PRIVATE)

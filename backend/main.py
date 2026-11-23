import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.api.limits import Limits
from backend.api.v3 import router as v3_router
from backend.services.common import Problem
from fastapi.middleware.cors import CORSMiddleware

from backend.api.health import router as health_router
from backend.api.tasks import router as tasks_router
from backend.db.store import initialize


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize()
    yield


app = FastAPI(
    title="The Missing Scratch API",
    description=(
        "Backend service for generating, evaluating, and validating "
        "camera-through-mirror inspection tasks."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

origins = [item.strip() for item in os.getenv("MISSING_SCRATCH_UI_ORIGINS", "").split(",") if item.strip()]
if "*" in origins:
    raise ValueError("Use explicit frontend origins for cookie-based predictions")
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type","Authorization","X-Judge-Code"])

app.add_middleware(Limits)

@app.exception_handler(Problem)
async def domain_error(request: Request, error: Problem):
    return JSONResponse({"detail":error.detail},status_code=error.status,headers={"Cache-Control":"no-store"})

from backend.api.evidence import router as evidence_router
app.include_router(evidence_router)
app.include_router(v3_router)
app.include_router(health_router)
app.include_router(tasks_router)

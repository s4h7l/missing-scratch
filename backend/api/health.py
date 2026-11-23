from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    api_version: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is ready to accept requests."""
    return HealthResponse(
        status="ready",
        service="missing-scratch-backend",
        api_version="v3",
    )

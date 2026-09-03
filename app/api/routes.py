"""HTTP endpoints exposed by the backend."""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Report that the API process is available."""
    settings = get_settings()
    return HealthResponse(status="ok", environment=settings.environment)

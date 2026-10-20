from fastapi import APIRouter

from src.core.config import get_settings
from src.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )

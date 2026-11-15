from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Liveness check")
async def health() -> HealthOut:
    return HealthOut(status="ok", version=get_settings().version)

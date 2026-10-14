from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.search_models import PlatformAvailabilityResponse
from app.security.auth import require_recruiter
from app.services.sources.registry import PLATFORMS, is_available


router = APIRouter(prefix="/api/sourcing", tags=["sourcing"], dependencies=[Depends(require_recruiter)])


@router.get("/platforms", response_model=list[PlatformAvailabilityResponse])
async def list_platforms(settings: Settings = Depends(get_settings)) -> list[PlatformAvailabilityResponse]:
    """Every sourcing platform, and whether this server is configured to use it."""
    return [
        PlatformAvailabilityResponse(platform=platform.value, available=is_available(platform, settings))
        for platform in PLATFORMS
    ]

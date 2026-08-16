from fastapi import APIRouter, Query

from app.modules.provider_dashboard.schemas import ProviderDashboardResponse
from app.modules.provider_dashboard.service import provider_dashboard_service

router = APIRouter(prefix="/provider", tags=["provider_dashboard"])


@router.get("/dashboard")
async def get_dashboard(
    provider_user_id: str = Query(...),
    provider_profile_id: str = Query(...),
) -> ProviderDashboardResponse:
    return await provider_dashboard_service.get_dashboard(
        provider_user_id=provider_user_id, provider_profile_id=provider_profile_id
    )

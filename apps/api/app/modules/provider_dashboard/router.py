from fastapi import APIRouter, Depends, Query

from app.modules.identity.dependencies import require_provider
from app.modules.identity.schemas import UserSummary
from app.modules.provider_dashboard.schemas import ProviderDashboardResponse
from app.modules.provider_dashboard.service import provider_dashboard_service

router = APIRouter(prefix="/provider", tags=["provider_dashboard"])


@router.get("/dashboard")
async def get_dashboard(
    provider_profile_id: str = Query(...),
    current_user: UserSummary = Depends(require_provider),
) -> ProviderDashboardResponse:
    return await provider_dashboard_service.get_dashboard(
        provider_user_id=current_user.id,
        provider_profile_id=provider_profile_id,
        acting_user_id=current_user.id,
    )

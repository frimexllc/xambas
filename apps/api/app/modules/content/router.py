from fastapi import APIRouter, Depends

from app.modules.admin.router import require_admin
from app.modules.admin.schemas import AdminSummary
from app.modules.content.schemas import (
    BusinessSettings,
    BusinessSettingsResponse,
    SiteContentResponse,
    SiteContentUpdateRequest,
)
from app.modules.content.service import content_service

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/site")
async def get_site_content() -> SiteContentResponse:
    """Publico: la pagina/landing lo consume sin autenticacion."""
    return await content_service.get_site_content()


@router.put("/site")
async def update_site_content(
    payload: SiteContentUpdateRequest, _: AdminSummary = Depends(require_admin)
) -> SiteContentResponse:
    return await content_service.update_site_content(payload)


@router.get("/business")
async def get_business_settings(
    _: AdminSummary = Depends(require_admin),
) -> BusinessSettingsResponse:
    return await content_service.get_business_settings()


@router.put("/business")
async def update_business_settings(
    payload: BusinessSettings, _: AdminSummary = Depends(require_admin)
) -> BusinessSettingsResponse:
    return await content_service.update_business_settings(payload)

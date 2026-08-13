from app.modules.content.repository import ContentRepository
from app.modules.content.schemas import (
    BrandSettings,
    BusinessSettings,
    BusinessSettingsResponse,
    LandingContent,
    SiteContentResponse,
    SiteContentUpdateRequest,
)


class ContentService:
    def __init__(self) -> None:
        self._repository = ContentRepository()

    async def get_site_content(self) -> SiteContentResponse:
        document = await self._repository.get_site_content()
        if document is None:
            return SiteContentResponse(
                module="content", brand=BrandSettings(), landing=LandingContent(), updated_at=None
            )
        return SiteContentResponse(
            module="content",
            brand=BrandSettings(**document["brand"]),
            landing=LandingContent(**document["landing"]),
            updated_at=document.get("updated_at"),
        )

    async def update_site_content(self, payload: SiteContentUpdateRequest) -> SiteContentResponse:
        document = await self._repository.upsert_site_content(
            brand=payload.brand.model_dump(), landing=payload.landing.model_dump()
        )
        return SiteContentResponse(
            module="content",
            brand=BrandSettings(**document["brand"]),
            landing=LandingContent(**document["landing"]),
            updated_at=document["updated_at"],
        )

    async def get_business_settings(self) -> BusinessSettingsResponse:
        document = await self._repository.get_business_settings()
        if document is None:
            return BusinessSettingsResponse(
                module="content", business=BusinessSettings(), updated_at=None
            )
        return BusinessSettingsResponse(
            module="content",
            business=BusinessSettings(**document["business"]),
            updated_at=document.get("updated_at"),
        )

    async def update_business_settings(self, business: BusinessSettings) -> BusinessSettingsResponse:
        document = await self._repository.upsert_business_settings(business=business.model_dump())
        return BusinessSettingsResponse(
            module="content",
            business=BusinessSettings(**document["business"]),
            updated_at=document["updated_at"],
        )


content_service = ContentService()

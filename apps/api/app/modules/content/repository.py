from datetime import datetime, timezone
from typing import Any

from app.core.database import get_database

SITE_CONTENT_ID = "site_content"
BUSINESS_SETTINGS_ID = "business_settings"


class ContentRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def get_site_content(self) -> dict[str, Any] | None:
        return await self._db.site_content.find_one({"_id": SITE_CONTENT_ID})

    async def upsert_site_content(self, *, brand: dict, landing: dict) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        document = {"_id": SITE_CONTENT_ID, "brand": brand, "landing": landing, "updated_at": now}
        await self._db.site_content.replace_one({"_id": SITE_CONTENT_ID}, document, upsert=True)
        return document

    async def get_business_settings(self) -> dict[str, Any] | None:
        return await self._db.site_content.find_one({"_id": BUSINESS_SETTINGS_ID})

    async def upsert_business_settings(self, *, business: dict) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        document = {"_id": BUSINESS_SETTINGS_ID, "business": business, "updated_at": now}
        await self._db.site_content.replace_one(
            {"_id": BUSINESS_SETTINGS_ID}, document, upsert=True
        )
        return document

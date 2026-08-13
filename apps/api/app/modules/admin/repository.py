from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId

from app.core.database import get_database


class AdminRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.admins.create_index("email", unique=True)
        await self._db.admin_sessions.create_index("token", unique=True)

    async def count_admins(self) -> int:
        return await self._db.admins.count_documents({})

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._db.admins.find_one({"email": email})

    async def get_by_id(self, admin_id: str) -> dict[str, Any] | None:
        return await self._db.admins.find_one({"_id": ObjectId(admin_id)})

    async def create_admin(
        self, *, name: str, email: str, password_hash: str, role: str
    ) -> dict[str, Any]:
        document = {
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await self._db.admins.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def list_admins(self) -> list[dict[str, Any]]:
        cursor = self._db.admins.find().sort("created_at", 1)
        return await cursor.to_list(length=200)

    async def create_session(self, *, admin_id: str, token: str, ttl_hours: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        document = {
            "admin_id": admin_id,
            "token": token,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=ttl_hours)).isoformat(),
        }
        result = await self._db.admin_sessions.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_session_by_token(self, token: str) -> dict[str, Any] | None:
        return await self._db.admin_sessions.find_one({"token": token})

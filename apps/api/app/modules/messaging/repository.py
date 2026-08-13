from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.core.database import get_database


class MessagingRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.threads.create_index("match_id", unique=True)
        await self._db.threads.create_index("client_id")
        await self._db.threads.create_index("provider_user_id")
        await self._db.messages.create_index("thread_id")
        await self._db.messages.create_index("created_at")

    async def get_thread_by_match_id(self, match_id: str) -> dict[str, Any] | None:
        return await self._db.threads.find_one({"match_id": match_id})

    async def create_thread(
        self,
        *,
        match_id: str,
        request_id: str,
        client_id: str,
        provider_user_id: str,
    ) -> dict[str, Any]:
        document = {
            "match_id": match_id,
            "request_id": request_id,
            "client_id": client_id,
            "provider_user_id": provider_user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_message_at": None,
        }
        result = await self._db.threads.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_thread_by_id(self, thread_id: str) -> dict[str, Any] | None:
        return await self._db.threads.find_one({"_id": ObjectId(thread_id)})

    async def create_message(
        self,
        *,
        thread_id: str,
        sender_id: str,
        sender_role: str,
        body: str,
        raw_body: str,
        flagged: bool,
        flag_reasons: list[str],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        document = {
            "thread_id": thread_id,
            "sender_id": sender_id,
            "sender_role": sender_role,
            "body": body,
            "raw_body": raw_body,
            "flagged": flagged,
            "flag_reasons": flag_reasons,
            "created_at": now.isoformat(),
        }
        result = await self._db.messages.insert_one(document)
        document["_id"] = result.inserted_id
        await self._db.threads.update_one(
            {"_id": ObjectId(thread_id)},
            {"$set": {"last_message_at": now.isoformat()}},
        )
        return document

    async def list_messages(self, thread_id: str) -> list[dict[str, Any]]:
        cursor = self._db.messages.find({"thread_id": thread_id}).sort("created_at", 1)
        return await cursor.to_list(length=500)

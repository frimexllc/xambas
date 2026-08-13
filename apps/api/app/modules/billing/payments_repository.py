from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.core.database import get_database


class PaymentsRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.payments.create_index("match_id")
        await self._db.payments.create_index("client_id")
        await self._db.payments.create_index("provider_user_id")
        await self._db.payments.create_index("stripe_payment_intent_id", unique=True, sparse=True)

    async def create_payment(self, document: dict[str, Any]) -> dict[str, Any]:
        document = {
            **document,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": None,
            "released_at": None,
        }
        result = await self._db.payments.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_by_id(self, payment_id: str) -> dict[str, Any] | None:
        return await self._db.payments.find_one({"_id": ObjectId(payment_id)})

    async def get_active_payment_for_match(self, match_id: str) -> dict[str, Any] | None:
        cursor = self._db.payments.find(
            {"match_id": match_id, "status": {"$in": ["pending", "held_in_escrow"]}}
        ).sort("created_at", -1)
        results = await cursor.to_list(length=1)
        return results[0] if results else None

    async def update_fields(self, payment_id: str, fields: dict[str, Any]) -> None:
        fields = {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}
        await self._db.payments.update_one({"_id": ObjectId(payment_id)}, {"$set": fields})

    async def list_for_client(self, client_id: str) -> list[dict[str, Any]]:
        cursor = self._db.payments.find({"client_id": client_id}).sort("created_at", -1)
        return await cursor.to_list(length=200)

    async def list_for_provider(self, provider_user_id: str) -> list[dict[str, Any]]:
        cursor = self._db.payments.find({"provider_user_id": provider_user_id}).sort("created_at", -1)
        return await cursor.to_list(length=200)

    async def list_all(self) -> list[dict[str, Any]]:
        cursor = self._db.payments.find().sort("created_at", -1)
        return await cursor.to_list(length=500)

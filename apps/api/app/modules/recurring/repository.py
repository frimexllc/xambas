from typing import Any

from bson import ObjectId

from app.core.database import get_database


class RecurringRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.subscriptions.create_index("client_id")
        await self._db.subscriptions.create_index("status")
        await self._db.subscription_occurrences.create_index("subscription_id")

    async def create_subscription(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self._db.subscriptions.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_subscription_by_id(self, subscription_id: str) -> dict[str, Any] | None:
        return await self._db.subscriptions.find_one({"_id": ObjectId(subscription_id)})

    async def list_subscriptions(self, client_id: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if client_id is not None:
            query["client_id"] = client_id
        cursor = self._db.subscriptions.find(query).sort("_id", -1)
        return await cursor.to_list(length=200)

    async def update_subscription(self, subscription_id: str, fields: dict[str, Any]) -> None:
        await self._db.subscriptions.update_one(
            {"_id": ObjectId(subscription_id)},
            {"$set": fields},
        )

    async def create_occurrence(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self._db.subscription_occurrences.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def list_occurrences(self, subscription_id: str) -> list[dict[str, Any]]:
        cursor = self._db.subscription_occurrences.find(
            {"subscription_id": subscription_id}
        ).sort("_id", -1)
        return await cursor.to_list(length=200)

    async def count_occurrences(self, subscription_id: str) -> int:
        return await self._db.subscription_occurrences.count_documents(
            {"subscription_id": subscription_id}
        )

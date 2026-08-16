from typing import Any

from bson import ObjectId

from app.core.database import get_database


class MilestonesRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.milestone_plans.create_index("match_id")
        await self._db.milestone_plans.create_index("client_id")
        await self._db.milestone_plans.create_index("provider_user_id")

    async def create_plan(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self._db.milestone_plans.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_plan_by_id(self, plan_id: str) -> dict[str, Any] | None:
        return await self._db.milestone_plans.find_one({"_id": ObjectId(plan_id)})

    async def get_plan_by_match(self, match_id: str) -> dict[str, Any] | None:
        return await self._db.milestone_plans.find_one({"match_id": match_id})

    async def list_plans(
        self, *, client_id: str | None = None, provider_user_id: str | None = None
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if client_id is not None:
            query["client_id"] = client_id
        if provider_user_id is not None:
            query["provider_user_id"] = provider_user_id
        cursor = self._db.milestone_plans.find(query).sort("_id", -1)
        return await cursor.to_list(length=200)

    async def update_plan(self, plan_id: str, fields: dict[str, Any]) -> None:
        await self._db.milestone_plans.update_one({"_id": ObjectId(plan_id)}, {"$set": fields})

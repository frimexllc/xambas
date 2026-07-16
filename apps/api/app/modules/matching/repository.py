from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from app.core.database import get_database
from app.modules.matching.schemas import CategoryCreateRequest, ServiceRequestCreateRequest


class MatchingRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.categories.create_index([("name", 1), ("parent_id", 1)], unique=True)
        await self._db.categories.create_index("parent_id")
        await self._db.service_requests.create_index("client_id")
        await self._db.service_requests.create_index("category_id")
        await self._db.service_requests.create_index("status")
        await self._db.service_requests.create_index("coverage_zone")
        await self._db.matches.create_index([("request_id", 1), ("provider_profile_id", 1)], unique=True)
        await self._db.matches.create_index("request_id")
        await self._db.matches.create_index("provider_user_id")

    async def create_category(self, payload: CategoryCreateRequest) -> dict[str, Any]:
        document = {
            "name": payload.name.strip(),
            "parent_id": payload.parent_id,
            "attributes_schema": payload.attributes_schema,
            "pricing_mode": payload.pricing_mode,
            "risk_level": payload.risk_level,
        }
        result = await self._db.categories.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def upsert_category(
        self,
        *,
        name: str,
        parent_id: str | None,
        attributes_schema: dict[str, Any],
        pricing_mode: str,
        risk_level: str,
    ) -> dict[str, Any]:
        normalized_name = name.strip()
        query = {"name": normalized_name, "parent_id": parent_id}
        update = {
            "$set": {
                "attributes_schema": attributes_schema,
                "pricing_mode": pricing_mode,
                "risk_level": risk_level,
            },
            "$setOnInsert": {
                "name": normalized_name,
                "parent_id": parent_id,
            },
        }
        result = await self._db.categories.find_one_and_update(
            query,
            update,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if result is not None:
            return result
        return await self._db.categories.find_one(query)

    async def get_category_by_id(self, category_id: str) -> dict[str, Any] | None:
        return await self._db.categories.find_one({"_id": ObjectId(category_id)})

    async def list_categories(self, parent_id: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if parent_id is not None:
            query["parent_id"] = parent_id
        cursor = self._db.categories.find(query).sort("name", 1)
        return await cursor.to_list(length=200)

    async def create_service_request(
        self,
        payload: ServiceRequestCreateRequest,
        *,
        category_name: str,
        pricing_mode: str,
        risk_level: str,
    ) -> dict[str, Any]:
        document = {
            "client_id": payload.client_id,
            "category_id": payload.category_id,
            "category_name": category_name,
            "title": payload.title.strip(),
            "description": payload.description.strip(),
            "pricing_mode": pricing_mode,
            "risk_level": risk_level,
            "country_code": payload.country_code.strip().upper(),
            "city": payload.city.strip(),
            "coverage_zone": payload.coverage_zone.strip(),
            "budget_amount": payload.budget_amount,
            "requested_for": payload.requested_for,
            "attributes": payload.attributes,
            "status": "open",
        }
        result = await self._db.service_requests.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_service_request_by_id(self, request_id: str) -> dict[str, Any] | None:
        return await self._db.service_requests.find_one({"_id": ObjectId(request_id)})

    async def list_service_requests(self, client_id: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if client_id is not None:
            query["client_id"] = client_id
        cursor = self._db.service_requests.find(query).sort("_id", -1)
        return await cursor.to_list(length=200)

    async def update_service_request_status(self, request_id: str, status: str) -> None:
        await self._db.service_requests.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": status}},
        )

    async def list_provider_profiles_for_matching(
        self,
        *,
        category_ids: list[str],
        coverage_zone: str,
    ) -> list[dict[str, Any]]:
        query = {
            "categories": {"$in": category_ids},
            "coverage_zones": coverage_zone,
        }
        cursor = self._db.provider_profiles.find(query).sort("rating_avg", -1)
        return await cursor.to_list(length=100)

    async def upsert_match(
        self,
        *,
        request_id: str,
        provider_profile: dict[str, Any],
        score: int,
        reasons: list[str],
    ) -> dict[str, Any]:
        query = {
            "request_id": request_id,
            "provider_profile_id": str(provider_profile["_id"]),
        }
        update = {
            "$set": {
                "provider_user_id": provider_profile["user_id"],
                "provider_business_name": provider_profile["business_name"],
                "provider_categories": provider_profile["categories"],
                "coverage_zones": provider_profile["coverage_zones"],
                "score": score,
                "reasons": reasons,
                "status": "suggested",
            },
            "$setOnInsert": {
                "request_id": request_id,
                "provider_profile_id": str(provider_profile["_id"]),
            },
        }
        result = await self._db.matches.find_one_and_update(
            query,
            update,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if result is not None:
            return result
        return await self._db.matches.find_one(query)

    async def list_matches_for_request(self, request_id: str) -> list[dict[str, Any]]:
        cursor = self._db.matches.find({"request_id": request_id}).sort([("score", -1), ("provider_business_name", 1)])
        return await cursor.to_list(length=100)

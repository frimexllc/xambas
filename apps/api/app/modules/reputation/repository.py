from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.core.database import get_database


class ReputationRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.reviews.create_index([("request_id", 1), ("client_id", 1)], unique=True)
        await self._db.reviews.create_index("provider_profile_id")

    async def create_review(
        self,
        *,
        request_id: str,
        provider_profile_id: str,
        client_id: str,
        rating: int,
        comment: str | None,
    ) -> dict[str, Any]:
        document = {
            "request_id": request_id,
            "provider_profile_id": provider_profile_id,
            "client_id": client_id,
            "rating": rating,
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await self._db.reviews.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def list_reviews_for_provider(self, provider_profile_id: str) -> list[dict[str, Any]]:
        cursor = self._db.reviews.find({"provider_profile_id": provider_profile_id}).sort(
            "created_at", -1
        )
        return await cursor.to_list(length=200)

    async def list_all_reviews(self) -> list[dict[str, Any]]:
        cursor = self._db.reviews.find().sort("created_at", -1)
        return await cursor.to_list(length=500)

    async def get_review_by_id(self, review_id: str) -> dict[str, Any] | None:
        return await self._db.reviews.find_one({"_id": ObjectId(review_id)})

    async def delete_review(self, review_id: str) -> None:
        await self._db.reviews.delete_one({"_id": ObjectId(review_id)})

    async def get_provider_profile(self, provider_profile_id: str) -> dict[str, Any] | None:
        return await self._db.provider_profiles.find_one({"_id": ObjectId(provider_profile_id)})

    async def update_provider_rating(
        self,
        provider_profile_id: str,
        new_rating_avg: float,
        jobs_completed_increment: int,
    ) -> None:
        await self._db.provider_profiles.update_one(
            {"_id": ObjectId(provider_profile_id)},
            {
                "$set": {"rating_avg": new_rating_avg},
                "$inc": {"jobs_completed": jobs_completed_increment},
            },
        )

    async def set_provider_rating(
        self, provider_profile_id: str, rating_avg: float, jobs_completed: int
    ) -> None:
        await self._db.provider_profiles.update_one(
            {"_id": ObjectId(provider_profile_id)},
            {"$set": {"rating_avg": rating_avg, "jobs_completed": jobs_completed}},
        )

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.core.database import get_database
from app.modules.identity.schemas import OtpRequestPayload, ProviderProfileDraft, UserBootstrapRequest


class IdentityRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.users.create_index("email", unique=True)
        await self._db.users.create_index("phone", unique=True)
        await self._db.provider_profiles.create_index("user_id", unique=True)
        await self._db.otp_challenges.create_index("expires_at", expireAfterSeconds=0)
        await self._db.otp_challenges.create_index("external_sid")
        await self._db.sessions.create_index("expires_at", expireAfterSeconds=0)
        await self._db.sessions.create_index("token_hash", unique=True)

    async def create_user(self, payload: UserBootstrapRequest) -> dict[str, Any]:
        document = {
            "role": payload.role,
            "email": payload.email.strip().lower(),
            "phone": payload.phone.strip(),
            "phone_verified": False,
            "auth_provider": "otp",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "locale": payload.locale,
            "kyc_status": "pending",
        }
        result = await self._db.users.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def create_provider_profile(
        self,
        user_id: str,
        provider_profile: ProviderProfileDraft,
    ) -> dict[str, Any]:
        document = {
            "user_id": user_id,
            "business_name": provider_profile.business_name,
            "categories": provider_profile.categories,
            "coverage_zones": provider_profile.coverage_zones,
            "tier": "nuevo",
            "rating_avg": 0.0,
            "jobs_completed": 0,
            "cancellation_rate": 0.0,
            "insurance_verified": provider_profile.insurance_verified,
            "license_verified": provider_profile.license_verified,
            "portfolio_media": [],
            "stripe_connect_account_id": None,
            "mercadopago_account_id": None,
        }
        result = await self._db.provider_profiles.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await self._db.users.find_one({"_id": ObjectId(user_id)})

    async def get_provider_profile_by_user_id(self, user_id: str) -> dict[str, Any] | None:
        return await self._db.provider_profiles.find_one({"user_id": user_id})

    async def create_otp_challenge(
        self,
        user_id: str,
        payload: OtpRequestPayload,
        *,
        provider: str,
        code_hash: str | None,
        external_sid: str | None,
        max_attempts: int,
        expires_at: datetime,
    ) -> dict[str, Any]:
        document = {
            "user_id": user_id,
            "purpose": payload.purpose,
            "channel": payload.channel,
            "provider": provider,
            "code_hash": code_hash,
            "external_sid": external_sid,
            "status": "pending",
            "attempts": 0,
            "max_attempts": max_attempts,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
        }
        result = await self._db.otp_challenges.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_otp_challenge(self, challenge_id: str, user_id: str) -> dict[str, Any] | None:
        return await self._db.otp_challenges.find_one(
            {
                "_id": ObjectId(challenge_id),
                "user_id": user_id,
            }
        )

    async def increment_otp_attempts(self, challenge_id: str) -> None:
        await self._db.otp_challenges.update_one(
            {"_id": ObjectId(challenge_id)},
            {"$inc": {"attempts": 1}},
        )

    async def mark_otp_challenge_as_used(self, challenge_id: str) -> None:
        await self._db.otp_challenges.update_one(
            {"_id": ObjectId(challenge_id)},
            {"$set": {"status": "verified"}},
        )

    async def mark_otp_challenge_as_failed(self, challenge_id: str) -> None:
        await self._db.otp_challenges.update_one(
            {"_id": ObjectId(challenge_id)},
            {"$set": {"status": "failed"}},
        )

    async def mark_user_phone_verified(self, user_id: str) -> None:
        await self._db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"phone_verified": True}},
        )

    async def create_session(
        self,
        user_id: str,
        token_hash: str,
        device_name: str,
        expires_at: datetime,
    ) -> dict[str, Any]:
        document = {
            "user_id": user_id,
            "token_hash": token_hash,
            "device_name": device_name,
            "created_at": datetime.now(timezone.utc),
            "last_seen_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "status": "active",
        }
        result = await self._db.sessions.insert_one(document)
        document["_id"] = result.inserted_id
        return document

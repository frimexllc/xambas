from datetime import timezone

from bson.errors import InvalidId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.modules.identity.auth import build_expiration, build_session_expiration, build_session_token, hash_secret, utc_now
from app.modules.identity.providers.base import OtpProvider
from app.modules.identity.providers.dev_provider import DevOtpProvider
from app.modules.identity.providers.twilio_verify_provider import TwilioVerifyProvider
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import (
    IdentityStatusResponse,
    IdentityUserResponse,
    OtpRequestPayload,
    OtpRequestResponse,
    OtpVerifyPayload,
    OtpVerifyResponse,
    ProviderProfileSummary,
    SessionSummary,
    UserBootstrapRequest,
    UserBootstrapResponse,
    UserSummary,
)


class IdentityService:
    def __init__(self) -> None:
        self._repository = IdentityRepository()

    def get_status(self) -> IdentityStatusResponse:
        return IdentityStatusResponse(
            module="identity",
            status="ready",
            supported_roles=["client", "provider", "both"],
            supported_kyc_statuses=["pending", "in_review", "verified", "rejected"],
        )

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    async def bootstrap_user(self, payload: UserBootstrapRequest) -> UserBootstrapResponse:
        next_steps = [
            "validar OTP de telefono",
            "verificar login y sesion",
        ]

        try:
            user_document = await self._repository.create_user(payload)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ya existe un usuario con ese email o telefono",
            ) from exc
        provider_profile = None

        if payload.role in {"provider", "both"}:
            if payload.provider_profile is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="provider_profile es obligatorio para roles provider y both",
                )

            provider_profile_document = await self._repository.create_provider_profile(
                user_id=str(user_document["_id"]),
                provider_profile=payload.provider_profile,
            )
            provider_profile = self._serialize_provider_profile(provider_profile_document)
            next_steps.extend(
                [
                    "iniciar verificacion KYC",
                    "cargar licencias y seguros si la categoria lo exige",
                    "conectar cuenta de pagos cuando billing quede operativo",
                ]
            )

        return UserBootstrapResponse(
            module="identity",
            status="created",
            user=self._serialize_user(user_document),
            provider_profile=provider_profile,
            next_steps=next_steps,
        )

    async def get_user(self, user_id: str) -> IdentityUserResponse:
        try:
            user_document = await self._repository.get_user_by_id(user_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id invalido",
            ) from exc

        if user_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user no encontrado",
            )

        provider_profile_document = await self._repository.get_provider_profile_by_user_id(user_id)
        return IdentityUserResponse(
            module="identity",
            user=self._serialize_user(user_document),
            provider_profile=(
                self._serialize_provider_profile(provider_profile_document)
                if provider_profile_document
                else None
            ),
        )

    async def request_otp(self, payload: OtpRequestPayload) -> OtpRequestResponse:
        user_document = await self._get_user_document_or_404(payload.user_id)
        dispatch = self._build_otp_provider().request_code(user_document["phone"], payload.channel)
        expires_at = build_expiration(settings.otp_ttl_minutes)
        challenge_document = await self._repository.create_otp_challenge(
            user_id=payload.user_id,
            payload=payload,
            provider=dispatch.provider,
            code_hash=dispatch.code_hash,
            external_sid=dispatch.external_sid,
            max_attempts=settings.otp_max_attempts,
            expires_at=expires_at,
        )
        return OtpRequestResponse(
            module="identity",
            status="otp_sent",
            challenge_id=str(challenge_document["_id"]),
            expires_at=expires_at.isoformat(),
            delivery_target=user_document["phone"],
            debug_code=dispatch.debug_code,
        )

    async def verify_otp(self, payload: OtpVerifyPayload) -> OtpVerifyResponse:
        user_document = await self._get_user_document_or_404(payload.user_id)
        challenge_document = await self._get_challenge_or_404(payload.challenge_id, payload.user_id)

        if challenge_document["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="el desafio OTP ya no esta pendiente",
            )
        if challenge_document["attempts"] >= challenge_document["max_attempts"]:
            await self._repository.mark_otp_challenge_as_failed(payload.challenge_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="se alcanzo el maximo de intentos OTP",
            )

        expires_at = challenge_document["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < utc_now():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="el codigo OTP expiro",
            )

        verification = self._build_otp_provider(challenge_document["provider"]).verify_code(
            phone=user_document["phone"],
            code=payload.code,
            external_sid=challenge_document.get("external_sid"),
            code_hash=challenge_document.get("code_hash"),
        )
        if not verification.approved:
            await self._repository.increment_otp_attempts(payload.challenge_id)
            if challenge_document["attempts"] + 1 >= challenge_document["max_attempts"]:
                await self._repository.mark_otp_challenge_as_failed(payload.challenge_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"codigo OTP invalido: {verification.status}",
            )

        await self._repository.mark_otp_challenge_as_used(payload.challenge_id)
        await self._repository.mark_user_phone_verified(payload.user_id)

        token = build_session_token()
        session_document = await self._repository.create_session(
            user_id=payload.user_id,
            token_hash=hash_secret(token),
            device_name=payload.device_name,
            expires_at=build_session_expiration(settings.session_ttl_hours),
        )
        refreshed_user = await self._get_user_document_or_404(payload.user_id)

        return OtpVerifyResponse(
            module="identity",
            status="verified",
            user=self._serialize_user(refreshed_user),
            session=SessionSummary(
                session_id=str(session_document["_id"]),
                token=token,
                expires_at=session_document["expires_at"].isoformat(),
                user_id=payload.user_id,
                device_name=session_document["device_name"],
            ),
        )

    def _build_otp_provider(self, provider_name: str | None = None) -> OtpProvider:
        selected_provider = provider_name or settings.otp_provider
        if selected_provider == "twilio":
            return TwilioVerifyProvider()
        return DevOtpProvider()

    async def _get_user_document_or_404(self, user_id: str) -> dict:
        try:
            user_document = await self._repository.get_user_by_id(user_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id invalido",
            ) from exc

        if user_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user no encontrado",
            )
        return user_document

    async def _get_challenge_or_404(self, challenge_id: str, user_id: str) -> dict:
        try:
            challenge_document = await self._repository.get_otp_challenge(challenge_id, user_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="challenge_id invalido",
            ) from exc

        if challenge_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="desafio OTP no encontrado",
            )
        return challenge_document

    def _serialize_user(self, document: dict) -> UserSummary:
        return UserSummary(
            id=str(document["_id"]),
            role=document["role"],
            email=document["email"],
            phone=document["phone"],
            auth_provider=document["auth_provider"],
            locale=document["locale"],
            phone_verified=document["phone_verified"],
            kyc_status=document["kyc_status"],
            created_at=document["created_at"],
        )

    def _serialize_provider_profile(self, document: dict) -> ProviderProfileSummary:
        return ProviderProfileSummary(
            id=str(document["_id"]),
            user_id=document["user_id"],
            business_name=document["business_name"],
            categories=document["categories"],
            coverage_zones=document["coverage_zones"],
            tier=document["tier"],
            rating_avg=document["rating_avg"],
            jobs_completed=document["jobs_completed"],
            cancellation_rate=document["cancellation_rate"],
            insurance_verified=document["insurance_verified"],
            license_verified=document["license_verified"],
            portfolio_media=document["portfolio_media"],
            stripe_connect_account_id=document["stripe_connect_account_id"],
            mercadopago_account_id=document["mercadopago_account_id"],
        )


identity_service = IdentityService()

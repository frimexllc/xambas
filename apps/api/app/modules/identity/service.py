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
    LoginStartRequest,
    LoginStartResponse,
    OtpRequestPayload,
    OtpRequestResponse,
    OtpVerifyPayload,
    OtpVerifyResponse,
    ProviderProfileAdminUpdateRequest,
    ProviderProfileListResponse,
    ProviderProfileSummary,
    SessionSummary,
    UserAdminUpdateRequest,
    UserBootstrapRequest,
    UserBootstrapResponse,
    UserListResponse,
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

    async def start_login(self, payload: LoginStartRequest) -> LoginStartResponse:
        """Login de una cuenta existente: identificador (teléfono o correo) -> OTP.

        Devuelve el ``user_id`` y el ``challenge_id`` para completar con
        ``POST /identity/otp/verify`` (que es lo que crea la sesión).
        """
        identifier = payload.identifier.strip()
        user_document = await self._repository.get_user_by_phone(identifier)
        if user_document is None:
            user_document = await self._repository.get_user_by_email(identifier)
        if user_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="no hay una cuenta con ese telefono o correo",
            )
        if not user_document.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="la cuenta esta desactivada",
            )

        user_id = str(user_document["_id"])
        otp_response = await self.request_otp(
            OtpRequestPayload(user_id=user_id, purpose="login", channel=payload.channel)
        )
        return LoginStartResponse(
            module="identity",
            status="otp_sent",
            user_id=user_id,
            challenge_id=otp_response.challenge_id,
            expires_at=otp_response.expires_at,
            delivery_target=otp_response.delivery_target,
            debug_code=otp_response.debug_code,
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

    async def get_user_from_token(self, token: str) -> UserSummary:
        """Resuelve el usuario dueño de un token de sesión (header Bearer).

        El token se guarda hasheado; Mongo tiene un índice TTL sobre
        ``expires_at`` pero la limpieza no es inmediata, así que revalidamos la
        expiración aquí.
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token de sesion vacio",
            )
        session_document = await self._repository.get_active_session_by_token_hash(hash_secret(token))
        if session_document is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token de sesion invalido o revocado",
            )
        expires_at = session_document["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < utc_now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="la sesion expiro, vuelve a verificar tu telefono",
            )
        user_document = await self._get_user_document_or_404(session_document["user_id"])
        if not user_document.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="la cuenta esta desactivada",
            )
        return self._serialize_user(user_document)

    async def list_users(self) -> UserListResponse:
        documents = await self._repository.list_users()
        return UserListResponse(
            module="identity",
            total=len(documents),
            items=[self._serialize_user(document) for document in documents],
        )

    async def update_user_admin(
        self, user_id: str, payload: UserAdminUpdateRequest
    ) -> UserSummary:
        await self._get_user_document_or_404(user_id)
        fields = {key: value for key, value in payload.model_dump().items() if value is not None}
        if fields:
            await self._repository.update_user_fields(user_id, fields)
        refreshed = await self._get_user_document_or_404(user_id)
        return self._serialize_user(refreshed)

    async def list_provider_profiles(self) -> ProviderProfileListResponse:
        documents = await self._repository.list_provider_profiles()
        return ProviderProfileListResponse(
            module="identity",
            total=len(documents),
            items=[self._serialize_provider_profile(document) for document in documents],
        )

    async def update_provider_profile_admin(
        self, provider_profile_id: str, payload: ProviderProfileAdminUpdateRequest
    ) -> ProviderProfileSummary:
        try:
            document = await self._repository.get_provider_profile_by_id(provider_profile_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="provider_profile_id invalido"
            ) from exc
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="provider_profile no encontrado"
            )
        fields = {key: value for key, value in payload.model_dump().items() if value is not None}
        if fields:
            await self._repository.update_provider_profile_fields(provider_profile_id, fields)
        refreshed = await self._repository.get_provider_profile_by_id(provider_profile_id)
        return self._serialize_provider_profile(refreshed)

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
            is_active=document.get("is_active", True),
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
            is_active=document.get("is_active", True),
        )


identity_service = IdentityService()

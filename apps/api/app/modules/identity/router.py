from fastapi import APIRouter, Request

from app.modules.identity.schemas import (
    IdentityStatusResponse,
    IdentityUserResponse,
    LoginStartRequest,
    LoginStartResponse,
    OtpRequestPayload,
    OtpRequestResponse,
    OtpVerifyPayload,
    OtpVerifyResponse,
    UserBootstrapRequest,
    UserBootstrapResponse,
)
from app.modules.identity.service import identity_service

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("/status")
def identity_status() -> IdentityStatusResponse:
    return identity_service.get_status()


@router.post("/bootstrap")
async def identity_bootstrap(payload: UserBootstrapRequest) -> UserBootstrapResponse:
    return await identity_service.bootstrap_user(payload)


@router.get("/users/{user_id}")
async def identity_get_user(user_id: str) -> IdentityUserResponse:
    return await identity_service.get_user(user_id)


def _client_ip(request: Request) -> str | None:
    # MVP: IP directa del socket. Detrás de un proxy/load balancer real, esto
    # debe leer X-Forwarded-For (del proxy de confianza, no del cliente).
    return request.client.host if request.client else None


@router.post("/login")
async def identity_login(payload: LoginStartRequest, request: Request) -> LoginStartResponse:
    """Inicia sesión en una cuenta existente (teléfono o correo → OTP).

    Se completa con ``POST /identity/otp/verify``.
    """
    return await identity_service.start_login(payload, client_ip=_client_ip(request))


@router.post("/otp/request")
async def identity_request_otp(
    payload: OtpRequestPayload, request: Request
) -> OtpRequestResponse:
    return await identity_service.request_otp(payload, client_ip=_client_ip(request))


@router.post("/otp/verify")
async def identity_verify_otp(payload: OtpVerifyPayload) -> OtpVerifyResponse:
    return await identity_service.verify_otp(payload)

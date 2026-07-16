from fastapi import APIRouter

from app.modules.identity.schemas import (
    IdentityStatusResponse,
    IdentityUserResponse,
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


@router.post("/otp/request")
async def identity_request_otp(payload: OtpRequestPayload) -> OtpRequestResponse:
    return await identity_service.request_otp(payload)


@router.post("/otp/verify")
async def identity_verify_otp(payload: OtpVerifyPayload) -> OtpVerifyResponse:
    return await identity_service.verify_otp(payload)

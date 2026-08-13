from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.modules.admin.schemas import (
    AdminBootstrapRequest,
    AdminCreateRequest,
    AdminListResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminStatusResponse,
    AdminSummary,
)
from app.modules.admin.service import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(authorization: str | None = Header(default=None)) -> AdminSummary:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de administrador (header Authorization: Bearer <token>)",
        )
    token = authorization.split(" ", 1)[1].strip()
    return await admin_service.get_admin_from_token(token)


async def require_super_admin(admin: AdminSummary = Depends(require_admin)) -> AdminSummary:
    if admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Esta accion requiere rol super_admin"
        )
    return admin


@router.get("/status")
async def admin_status() -> AdminStatusResponse:
    return await admin_service.get_status()


@router.post("/auth/bootstrap")
async def bootstrap_admin(payload: AdminBootstrapRequest) -> AdminLoginResponse:
    return await admin_service.bootstrap(payload)


@router.post("/auth/login")
async def login_admin(payload: AdminLoginRequest) -> AdminLoginResponse:
    return await admin_service.login(payload)


@router.get("/auth/me")
async def get_me(admin: AdminSummary = Depends(require_admin)) -> AdminSummary:
    return admin


@router.post("/admins")
async def create_admin(
    payload: AdminCreateRequest, _: AdminSummary = Depends(require_super_admin)
) -> AdminSummary:
    return await admin_service.create_admin(payload)


@router.get("/admins")
async def list_admins(_: AdminSummary = Depends(require_super_admin)) -> AdminListResponse:
    return await admin_service.list_admins()

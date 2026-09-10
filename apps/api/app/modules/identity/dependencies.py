"""Dependencias de FastAPI para autenticar usuarios (cliente/proveedor) por token.

El token lo emite ``POST /api/identity/otp/verify`` tras un OTP correcto y se
manda en cada request como ``Authorization: Bearer <token>``. Es el equivalente,
para usuarios finales, de ``require_admin`` en el módulo admin.
"""
from fastapi import Depends, Header, HTTPException, status

from app.modules.identity.schemas import UserSummary
from app.modules.identity.service import identity_service


async def get_current_user(authorization: str | None = Header(default=None)) -> UserSummary:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de sesion (header Authorization: Bearer <token>)",
        )
    token = authorization.split(" ", 1)[1].strip()
    return await identity_service.get_user_from_token(token)


async def require_client(user: UserSummary = Depends(get_current_user)) -> UserSummary:
    if user.role not in {"client", "both"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="esta accion es solo para cuentas de cliente",
        )
    return user

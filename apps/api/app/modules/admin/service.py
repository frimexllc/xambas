import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.modules.admin.repository import AdminRepository
from app.modules.admin.schemas import (
    AdminBootstrapRequest,
    AdminCreateRequest,
    AdminListResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminSessionSummary,
    AdminStatusResponse,
    AdminSummary,
)

SESSION_TTL_HOURS = 24


class AdminService:
    def __init__(self) -> None:
        self._repository = AdminRepository()

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    async def get_status(self) -> AdminStatusResponse:
        count = await self._repository.count_admins()
        return AdminStatusResponse(module="admin", status="ready", has_admins=count > 0)

    async def bootstrap(self, payload: AdminBootstrapRequest) -> AdminLoginResponse:
        count = await self._repository.count_admins()
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe al menos un administrador; pide que te creen una cuenta desde el panel.",
            )
        document = await self._repository.create_admin(
            name=payload.name.strip(),
            email=payload.email.lower().strip(),
            password_hash=hash_password(payload.password),
            role="super_admin",
        )
        return await self._issue_session(document)

    async def create_admin(self, payload: AdminCreateRequest) -> AdminSummary:
        existing = await self._repository.get_by_email(payload.email.lower().strip())
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un administrador con ese correo",
            )
        document = await self._repository.create_admin(
            name=payload.name.strip(),
            email=payload.email.lower().strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        return self._serialize_admin(document)

    async def list_admins(self) -> AdminListResponse:
        documents = await self._repository.list_admins()
        return AdminListResponse(
            module="admin",
            total=len(documents),
            items=[self._serialize_admin(document) for document in documents],
        )

    async def login(self, payload: AdminLoginRequest) -> AdminLoginResponse:
        document = await self._repository.get_by_email(payload.email.lower().strip())
        if document is None or not verify_password(payload.password, document["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contrasena invalidos",
            )
        return await self._issue_session(document)

    async def get_admin_from_token(self, token: str) -> AdminSummary:
        session_document = await self._repository.get_session_by_token(token)
        if session_document is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion invalida")
        expires_at = datetime.fromisoformat(session_document["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion expirada")
        admin_document = await self._repository.get_by_id(session_document["admin_id"])
        if admin_document is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrador no encontrado"
            )
        return self._serialize_admin(admin_document)

    async def _issue_session(self, admin_document: dict) -> AdminLoginResponse:
        token = secrets.token_urlsafe(32)
        session_document = await self._repository.create_session(
            admin_id=str(admin_document["_id"]), token=token, ttl_hours=SESSION_TTL_HOURS
        )
        return AdminLoginResponse(
            module="admin",
            status="ok",
            admin=self._serialize_admin(admin_document),
            session=AdminSessionSummary(
                session_id=str(session_document["_id"]),
                token=token,
                expires_at=session_document["expires_at"],
                admin_id=str(admin_document["_id"]),
            ),
        )

    def _serialize_admin(self, document: dict) -> AdminSummary:
        return AdminSummary(
            id=str(document["_id"]),
            name=document["name"],
            email=document["email"],
            role=document["role"],
            created_at=document["created_at"],
        )


admin_service = AdminService()

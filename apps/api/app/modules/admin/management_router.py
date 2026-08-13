from fastapi import APIRouter, Depends

from app.modules.admin.router import require_admin
from app.modules.admin.schemas import AdminSummary
from app.modules.identity.schemas import (
    ProviderProfileAdminUpdateRequest,
    ProviderProfileListResponse,
    ProviderProfileSummary,
    UserAdminUpdateRequest,
    UserListResponse,
    UserSummary,
)
from app.modules.identity.service import identity_service
from app.modules.matching.schemas import (
    CategoryCreateRequest,
    CategorySummary,
    CategoryUpdateRequest,
    ServiceRequestListResponse,
)
from app.modules.matching.service import matching_service
from app.modules.reputation.schemas import ReviewListResponse
from app.modules.reputation.service import reputation_service

router = APIRouter(prefix="/admin", tags=["admin-management"])


# ---------------------------------------------------------------------------
# Categorias (matching)
# ---------------------------------------------------------------------------


@router.post("/categories")
async def admin_create_category(
    payload: CategoryCreateRequest, _: AdminSummary = Depends(require_admin)
) -> CategorySummary:
    return await matching_service.create_category(payload)


@router.patch("/categories/{category_id}")
async def admin_update_category(
    category_id: str,
    payload: CategoryUpdateRequest,
    _: AdminSummary = Depends(require_admin),
) -> CategorySummary:
    return await matching_service.update_category(category_id, payload)


# ---------------------------------------------------------------------------
# Usuarios y proveedores (identity)
# ---------------------------------------------------------------------------


@router.get("/users")
async def admin_list_users(_: AdminSummary = Depends(require_admin)) -> UserListResponse:
    return await identity_service.list_users()


@router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: str,
    payload: UserAdminUpdateRequest,
    _: AdminSummary = Depends(require_admin),
) -> UserSummary:
    return await identity_service.update_user_admin(user_id, payload)


@router.get("/providers")
async def admin_list_providers(
    _: AdminSummary = Depends(require_admin),
) -> ProviderProfileListResponse:
    return await identity_service.list_provider_profiles()


@router.patch("/providers/{provider_profile_id}")
async def admin_update_provider(
    provider_profile_id: str,
    payload: ProviderProfileAdminUpdateRequest,
    _: AdminSummary = Depends(require_admin),
) -> ProviderProfileSummary:
    return await identity_service.update_provider_profile_admin(provider_profile_id, payload)


# ---------------------------------------------------------------------------
# Solicitudes de servicio (matching) - solo lectura para supervision
# ---------------------------------------------------------------------------


@router.get("/service-requests")
async def admin_list_service_requests(
    _: AdminSummary = Depends(require_admin),
) -> ServiceRequestListResponse:
    return await matching_service.list_service_requests(client_id=None)


# ---------------------------------------------------------------------------
# Resenas (reputation) - moderacion
# ---------------------------------------------------------------------------


@router.get("/reviews")
async def admin_list_reviews(_: AdminSummary = Depends(require_admin)) -> ReviewListResponse:
    return await reputation_service.list_all_reviews()


@router.delete("/reviews/{review_id}")
async def admin_delete_review(review_id: str, _: AdminSummary = Depends(require_admin)) -> dict:
    await reputation_service.delete_review(review_id)
    return {"module": "reputation", "status": "deleted", "review_id": review_id}

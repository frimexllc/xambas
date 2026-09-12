from fastapi import APIRouter, Depends, Query

from app.modules.identity.dependencies import get_current_user, require_client, require_provider
from app.modules.identity.schemas import UserSummary
from app.modules.matching.schemas import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategorySummary,
    MatchAcceptRequest,
    MatchListResponse,
    MatchingStatusResponse,
    MatchSummary,
    ServiceRequestCreateRequest,
    ServiceRequestListResponse,
    ServiceRequestResponse,
)
from app.modules.matching.service import matching_service

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("/status")
def matching_status() -> MatchingStatusResponse:
    return matching_service.get_status()


@router.post("/categories")
async def create_category(payload: CategoryCreateRequest) -> CategorySummary:
    return await matching_service.create_category(payload)


@router.get("/categories")
async def list_categories(parent_id: str | None = Query(default=None)) -> CategoryListResponse:
    return await matching_service.list_categories(parent_id=parent_id)


@router.get("/categories/{category_id}")
async def get_category(category_id: str) -> CategorySummary:
    return await matching_service.get_category(category_id)


@router.post("/service-requests")
async def create_service_request(
    payload: ServiceRequestCreateRequest,
    current_user: UserSummary = Depends(require_client),
) -> ServiceRequestResponse:
    payload = payload.model_copy(update={"client_id": current_user.id})
    return await matching_service.create_service_request(payload)


@router.get("/service-requests")
async def list_service_requests(
    current_user: UserSummary = Depends(require_client),
) -> ServiceRequestListResponse:
    return await matching_service.list_service_requests(client_id=current_user.id)


@router.get("/service-requests/{request_id}")
async def get_service_request(
    request_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> ServiceRequestResponse:
    return await matching_service.get_service_request(request_id, acting_user_id=current_user.id)


@router.post("/service-requests/{request_id}/run")
async def rerun_matching(
    request_id: str,
    current_user: UserSummary = Depends(require_client),
) -> MatchListResponse:
    return await matching_service.rerun_matching(request_id, acting_user_id=current_user.id)


@router.get("/service-requests/{request_id}/matches")
async def list_matches(
    request_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> MatchListResponse:
    return await matching_service.list_matches(request_id, acting_user_id=current_user.id)


@router.get("/providers/{provider_user_id}/matches")
async def list_matches_for_provider(
    provider_user_id: str,
    current_user: UserSummary = Depends(require_provider),
) -> MatchListResponse:
    # El proveedor solo ve sus propios matches, tome el id que tome la ruta.
    return await matching_service.list_matches_for_provider(current_user.id)


@router.post("/matches/{match_id}/accept")
async def accept_match(
    match_id: str,
    payload: MatchAcceptRequest,
    current_user: UserSummary = Depends(require_provider),
) -> MatchSummary:
    return await matching_service.accept_match(match_id, current_user.id)

from fastapi import APIRouter, Query

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
async def create_service_request(payload: ServiceRequestCreateRequest) -> ServiceRequestResponse:
    return await matching_service.create_service_request(payload)


@router.get("/service-requests")
async def list_service_requests(client_id: str | None = Query(default=None)) -> ServiceRequestListResponse:
    return await matching_service.list_service_requests(client_id=client_id)


@router.get("/service-requests/{request_id}")
async def get_service_request(request_id: str) -> ServiceRequestResponse:
    return await matching_service.get_service_request(request_id)


@router.post("/service-requests/{request_id}/run")
async def rerun_matching(request_id: str) -> MatchListResponse:
    return await matching_service.rerun_matching(request_id)


@router.get("/service-requests/{request_id}/matches")
async def list_matches(request_id: str) -> MatchListResponse:
    return await matching_service.list_matches(request_id)


@router.get("/providers/{provider_user_id}/matches")
async def list_matches_for_provider(provider_user_id: str) -> MatchListResponse:
    return await matching_service.list_matches_for_provider(provider_user_id)


@router.post("/matches/{match_id}/accept")
async def accept_match(match_id: str, payload: MatchAcceptRequest) -> MatchSummary:
    return await matching_service.accept_match(match_id, payload.provider_user_id)

from fastapi import APIRouter

from app.modules.reputation.schemas import (
    ProviderReputationResponse,
    ReputationStatusResponse,
    ReviewCreateRequest,
    ReviewSummary,
)
from app.modules.reputation.service import reputation_service

router = APIRouter(prefix="/reputation", tags=["reputation"])


@router.get("/status")
def reputation_status() -> ReputationStatusResponse:
    return reputation_service.get_status()


@router.post("/reviews")
async def create_review(payload: ReviewCreateRequest) -> ReviewSummary:
    return await reputation_service.create_review(payload)


@router.get("/providers/{provider_profile_id}")
async def get_provider_reputation(provider_profile_id: str) -> ProviderReputationResponse:
    return await reputation_service.get_provider_reputation(provider_profile_id)

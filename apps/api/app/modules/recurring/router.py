from fastapi import APIRouter, Query

from app.modules.recurring.schemas import (
    GenerateOccurrenceResponse,
    OccurrenceListResponse,
    RecurringStatusResponse,
    SubscriptionCreateRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
)
from app.modules.recurring.service import recurring_service

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("/status")
def recurring_status() -> RecurringStatusResponse:
    return recurring_service.get_status()


@router.post("/subscriptions")
async def create_subscription(payload: SubscriptionCreateRequest) -> SubscriptionResponse:
    return await recurring_service.create_subscription(payload)


@router.get("/subscriptions")
async def list_subscriptions(client_id: str | None = Query(default=None)) -> SubscriptionListResponse:
    return await recurring_service.list_subscriptions(client_id=client_id)


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str) -> SubscriptionResponse:
    return await recurring_service.get_subscription(subscription_id)


@router.post("/subscriptions/{subscription_id}/pause")
async def pause_subscription(subscription_id: str) -> SubscriptionResponse:
    return await recurring_service.set_status(subscription_id, "paused")


@router.post("/subscriptions/{subscription_id}/resume")
async def resume_subscription(subscription_id: str) -> SubscriptionResponse:
    return await recurring_service.set_status(subscription_id, "active")


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(subscription_id: str) -> SubscriptionResponse:
    return await recurring_service.set_status(subscription_id, "cancelled")


@router.post("/subscriptions/{subscription_id}/generate")
async def generate_occurrence(subscription_id: str) -> GenerateOccurrenceResponse:
    return await recurring_service.generate_occurrence(subscription_id)


@router.get("/subscriptions/{subscription_id}/occurrences")
async def list_occurrences(subscription_id: str) -> OccurrenceListResponse:
    return await recurring_service.list_occurrences(subscription_id)

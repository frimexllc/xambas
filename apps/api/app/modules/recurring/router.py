from fastapi import APIRouter, Depends

from app.modules.identity.dependencies import get_current_user
from app.modules.identity.schemas import UserSummary
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
async def create_subscription(
    payload: SubscriptionCreateRequest,
    current_user: UserSummary = Depends(get_current_user),
) -> SubscriptionResponse:
    # El cliente se toma del token, nunca del body: evita crear suscripciones
    # a nombre de otro usuario.
    payload = payload.model_copy(update={"client_id": current_user.id})
    return await recurring_service.create_subscription(payload)


@router.get("/subscriptions")
async def list_subscriptions(
    current_user: UserSummary = Depends(get_current_user),
) -> SubscriptionListResponse:
    return await recurring_service.list_subscriptions(client_id=current_user.id)


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> SubscriptionResponse:
    return await recurring_service.get_subscription(subscription_id, acting_user_id=current_user.id)


@router.post("/subscriptions/{subscription_id}/pause")
async def pause_subscription(
    subscription_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> SubscriptionResponse:
    return await recurring_service.set_status(subscription_id, "paused", acting_user_id=current_user.id)


@router.post("/subscriptions/{subscription_id}/resume")
async def resume_subscription(
    subscription_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> SubscriptionResponse:
    return await recurring_service.set_status(subscription_id, "active", acting_user_id=current_user.id)


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> SubscriptionResponse:
    return await recurring_service.set_status(
        subscription_id, "cancelled", acting_user_id=current_user.id
    )


@router.post("/subscriptions/{subscription_id}/generate")
async def generate_occurrence(
    subscription_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> GenerateOccurrenceResponse:
    return await recurring_service.generate_occurrence(
        subscription_id, acting_user_id=current_user.id
    )


@router.get("/subscriptions/{subscription_id}/occurrences")
async def list_occurrences(
    subscription_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> OccurrenceListResponse:
    return await recurring_service.list_occurrences(
        subscription_id, acting_user_id=current_user.id
    )

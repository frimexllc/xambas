from fastapi import APIRouter, Depends

from app.modules.identity.dependencies import get_current_user
from app.modules.identity.schemas import UserSummary
from app.modules.messaging.schemas import (
    MessageCreateRequest,
    MessageListResponse,
    MessageSummary,
    MessagingStatusResponse,
    ThreadGetOrCreateRequest,
    ThreadSummary,
)
from app.modules.messaging.service import messaging_service

router = APIRouter(prefix="/messaging", tags=["messaging"])


@router.get("/status")
def messaging_status() -> MessagingStatusResponse:
    return messaging_service.get_status()


@router.post("/threads")
async def get_or_create_thread(
    payload: ThreadGetOrCreateRequest,
    current_user: UserSummary = Depends(get_current_user),
) -> ThreadSummary:
    return await messaging_service.get_or_create_thread(payload, acting_user_id=current_user.id)


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> MessageListResponse:
    return await messaging_service.list_messages(thread_id, acting_user_id=current_user.id)


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    payload: MessageCreateRequest,
    current_user: UserSummary = Depends(get_current_user),
) -> MessageSummary:
    return await messaging_service.create_message(
        thread_id, payload, acting_user_id=current_user.id
    )

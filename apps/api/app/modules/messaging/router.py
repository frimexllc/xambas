from fastapi import APIRouter

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
async def get_or_create_thread(payload: ThreadGetOrCreateRequest) -> ThreadSummary:
    return await messaging_service.get_or_create_thread(payload)


@router.get("/threads/{thread_id}/messages")
async def list_messages(thread_id: str) -> MessageListResponse:
    return await messaging_service.list_messages(thread_id)


@router.post("/threads/{thread_id}/messages")
async def send_message(thread_id: str, payload: MessageCreateRequest) -> MessageSummary:
    return await messaging_service.create_message(thread_id, payload)

from bson.errors import InvalidId
from fastapi import HTTPException, status

from app.modules.matching.repository import MatchingRepository
from app.modules.messaging.leak_detection import detect_and_redact
from app.modules.messaging.repository import MessagingRepository
from app.modules.messaging.schemas import (
    MessageCreateRequest,
    MessageListResponse,
    MessageSummary,
    MessagingStatusResponse,
    ThreadGetOrCreateRequest,
    ThreadSummary,
)


class MessagingService:
    def __init__(self) -> None:
        self._repository = MessagingRepository()
        self._matching_repository = MatchingRepository()

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    def get_status(self) -> MessagingStatusResponse:
        return MessagingStatusResponse(
            module="messaging",
            status="ready",
            collections=["threads", "messages"],
        )

    async def get_or_create_thread(self, payload: ThreadGetOrCreateRequest) -> ThreadSummary:
        existing = await self._repository.get_thread_by_match_id(payload.match_id)
        if existing is not None:
            return await self._serialize_thread(existing)

        try:
            match_document = await self._matching_repository.get_match_by_id(payload.match_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="match_id invalido",
            ) from exc
        if match_document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match no encontrado")

        request_document = await self._matching_repository.get_service_request_by_id(
            match_document["request_id"]
        )
        if request_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="service_request no encontrado",
            )

        thread_document = await self._repository.create_thread(
            match_id=payload.match_id,
            request_id=match_document["request_id"],
            client_id=request_document["client_id"],
            provider_user_id=match_document["provider_user_id"],
        )
        return await self._serialize_thread(thread_document)

    async def list_messages(self, thread_id: str) -> MessageListResponse:
        await self._get_thread_or_404(thread_id)
        documents = await self._repository.list_messages(thread_id)
        return MessageListResponse(
            module="messaging",
            thread_id=thread_id,
            total=len(documents),
            items=[self._serialize_message(document) for document in documents],
        )

    async def create_message(self, thread_id: str, payload: MessageCreateRequest) -> MessageSummary:
        thread_document = await self._get_thread_or_404(thread_id)
        allowed_senders = {thread_document["client_id"], thread_document["provider_user_id"]}
        if payload.sender_id not in allowed_senders:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="sender_id no pertenece a este hilo",
            )

        raw_body = payload.body.strip()
        contact_unlocked = await self._is_contact_unlocked(thread_document["match_id"])
        if contact_unlocked:
            body, flagged, flag_reasons = raw_body, False, []
        else:
            body, flagged, flag_reasons = detect_and_redact(raw_body)

        document = await self._repository.create_message(
            thread_id=thread_id,
            sender_id=payload.sender_id,
            sender_role=payload.sender_role,
            body=body,
            raw_body=raw_body,
            flagged=flagged,
            flag_reasons=flag_reasons,
        )
        return self._serialize_message(document)

    async def _is_contact_unlocked(self, match_id: str) -> bool:
        # MVP: usamos el estado del match como proxy de "deposito/pago
        # confirmado" (seccion 12-13 del estudio) hasta conectar el
        # motor de pagos real. Una vez exista escrow real, esto debe
        # cambiar a verificar el estado del pago, no del match.
        match_document = await self._matching_repository.get_match_by_id(match_id)
        return match_document is not None and match_document.get("status") == "accepted"

    async def _get_thread_or_404(self, thread_id: str) -> dict:
        try:
            document = await self._repository.get_thread_by_id(thread_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="thread_id invalido",
            ) from exc
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hilo no encontrado")
        return document

    async def _serialize_thread(self, document: dict) -> ThreadSummary:
        return ThreadSummary(
            id=str(document["_id"]),
            match_id=document["match_id"],
            request_id=document["request_id"],
            client_id=document["client_id"],
            provider_user_id=document["provider_user_id"],
            created_at=document["created_at"],
            last_message_at=document.get("last_message_at"),
            contact_unlocked=await self._is_contact_unlocked(document["match_id"]),
        )

    def _serialize_message(self, document: dict) -> MessageSummary:
        return MessageSummary(
            id=str(document["_id"]),
            thread_id=document["thread_id"],
            sender_id=document["sender_id"],
            sender_role=document["sender_role"],
            body=document["body"],
            created_at=document["created_at"],
            flagged=document.get("flagged", False),
            flag_reasons=document.get("flag_reasons", []),
        )


messaging_service = MessagingService()

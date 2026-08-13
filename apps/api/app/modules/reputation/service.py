from bson.errors import InvalidId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.modules.reputation.repository import ReputationRepository
from app.modules.reputation.schemas import (
    ProviderReputationResponse,
    ReputationStatusResponse,
    ReviewCreateRequest,
    ReviewListResponse,
    ReviewSummary,
)


class ReputationService:
    def __init__(self) -> None:
        self._repository = ReputationRepository()

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    def get_status(self) -> ReputationStatusResponse:
        return ReputationStatusResponse(
            module="reputation",
            status="ready",
            collections=["reviews"],
        )

    async def create_review(self, payload: ReviewCreateRequest) -> ReviewSummary:
        provider_document = await self._get_provider_profile_or_404(payload.provider_profile_id)

        try:
            review_document = await self._repository.create_review(
                request_id=payload.request_id,
                provider_profile_id=payload.provider_profile_id,
                client_id=payload.client_id,
                rating=payload.rating,
                comment=payload.comment.strip() if payload.comment else None,
            )
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ya existe una resena de este cliente para este service_request",
            ) from exc

        current_avg = provider_document.get("rating_avg", 0.0)
        current_jobs = provider_document.get("jobs_completed", 0)
        new_avg = round(((current_avg * current_jobs) + payload.rating) / (current_jobs + 1), 2)
        await self._repository.update_provider_rating(payload.provider_profile_id, new_avg, 1)

        return self._serialize_review(review_document)

    async def get_provider_reputation(self, provider_profile_id: str) -> ProviderReputationResponse:
        provider_document = await self._get_provider_profile_or_404(provider_profile_id)
        review_documents = await self._repository.list_reviews_for_provider(provider_profile_id)
        return ProviderReputationResponse(
            module="reputation",
            provider_profile_id=provider_profile_id,
            rating_avg=provider_document.get("rating_avg", 0.0),
            jobs_completed=provider_document.get("jobs_completed", 0),
            reviews=[self._serialize_review(document) for document in review_documents],
        )

    async def list_all_reviews(self) -> ReviewListResponse:
        documents = await self._repository.list_all_reviews()
        return ReviewListResponse(
            module="reputation",
            total=len(documents),
            items=[self._serialize_review(document) for document in documents],
        )

    async def delete_review(self, review_id: str) -> None:
        try:
            review_document = await self._repository.get_review_by_id(review_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="review_id invalido"
            ) from exc
        if review_document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resena no encontrada")

        await self._repository.delete_review(review_id)

        remaining = await self._repository.list_reviews_for_provider(
            review_document["provider_profile_id"]
        )
        jobs_completed = len(remaining)
        rating_avg = (
            round(sum(item["rating"] for item in remaining) / jobs_completed, 2)
            if jobs_completed > 0
            else 0.0
        )
        await self._repository.set_provider_rating(
            review_document["provider_profile_id"], rating_avg, jobs_completed
        )

    async def _get_provider_profile_or_404(self, provider_profile_id: str) -> dict:
        try:
            document = await self._repository.get_provider_profile(provider_profile_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="provider_profile_id invalido",
            ) from exc
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="provider_profile no encontrado",
            )
        return document

    def _serialize_review(self, document: dict) -> ReviewSummary:
        return ReviewSummary(
            id=str(document["_id"]),
            request_id=document["request_id"],
            provider_profile_id=document["provider_profile_id"],
            client_id=document["client_id"],
            rating=document["rating"],
            comment=document.get("comment"),
            created_at=document["created_at"],
        )


reputation_service = ReputationService()

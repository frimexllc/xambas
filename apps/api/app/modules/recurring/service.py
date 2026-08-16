from datetime import date, datetime, timedelta, timezone

from bson.errors import InvalidId
from fastapi import HTTPException, status

from app.modules.identity.repository import IdentityRepository
from app.modules.matching.schemas import ServiceRequestCreateRequest
from app.modules.matching.service import matching_service
from app.modules.recurring.repository import RecurringRepository
from app.modules.recurring.schemas import (
    GenerateOccurrenceResponse,
    OccurrenceListResponse,
    OccurrenceSummary,
    RecurringStatusResponse,
    SubscriptionCreateRequest,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionSummary,
)

_FREQUENCY_LABELS = {
    "weekly": "Semanal",
    "biweekly": "Quincenal",
    "monthly": "Mensual",
}


class RecurringService:
    def __init__(self) -> None:
        self._repository = RecurringRepository()
        self._identity_repository = IdentityRepository()

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    def get_status(self) -> RecurringStatusResponse:
        return RecurringStatusResponse(
            module="recurring",
            status="ready",
            collections=["subscriptions", "subscription_occurrences"],
            supported_frequencies=list(_FREQUENCY_LABELS.keys()),
        )

    async def create_subscription(self, payload: SubscriptionCreateRequest) -> SubscriptionResponse:
        client_document = await self._get_user_document_or_404(payload.client_id)
        if client_document["role"] not in {"client", "both"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="solo un cliente puede crear una suscripcion",
            )

        category = await matching_service.get_category(payload.category_id)

        start = self._parse_date_or_400(payload.start_date) if payload.start_date else self._today()
        document = {
            "client_id": payload.client_id,
            "category_id": payload.category_id,
            "category_name": category.name,
            "title": payload.title.strip(),
            "description": payload.description.strip(),
            "pricing_mode": category.pricing_mode,
            "risk_level": category.risk_level,
            "country_code": payload.country_code.strip().upper(),
            "city": payload.city.strip(),
            "coverage_zone": payload.coverage_zone.strip(),
            "frequency": payload.frequency,
            "budget_amount": payload.budget_amount,
            "start_date": start.isoformat(),
            "next_run_date": start.isoformat(),
            "preferred_time": payload.preferred_time,
            "attributes": payload.attributes,
            "status": "active",
        }
        document = await self._repository.create_subscription(document)
        return SubscriptionResponse(
            module="recurring",
            subscription=await self._serialize_subscription(document),
        )

    async def list_subscriptions(self, client_id: str | None = None) -> SubscriptionListResponse:
        if client_id is not None:
            await self._get_user_document_or_404(client_id)
        documents = await self._repository.list_subscriptions(client_id=client_id)
        items = [await self._serialize_subscription(document) for document in documents]
        return SubscriptionListResponse(module="recurring", total=len(items), items=items)

    async def get_subscription(self, subscription_id: str) -> SubscriptionResponse:
        document = await self._get_subscription_document_or_404(subscription_id)
        return SubscriptionResponse(
            module="recurring",
            subscription=await self._serialize_subscription(document),
        )

    async def set_status(self, subscription_id: str, new_status: str) -> SubscriptionResponse:
        document = await self._get_subscription_document_or_404(subscription_id)
        if document["status"] == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="una suscripcion cancelada no puede cambiar de estado",
            )
        await self._repository.update_subscription(subscription_id, {"status": new_status})
        document["status"] = new_status
        return SubscriptionResponse(
            module="recurring",
            subscription=await self._serialize_subscription(document),
        )

    async def generate_occurrence(self, subscription_id: str) -> GenerateOccurrenceResponse:
        document = await self._get_subscription_document_or_404(subscription_id)
        if document["status"] != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="solo una suscripcion activa puede generar una visita",
            )

        scheduled_date = document["next_run_date"]
        service_request = await matching_service.create_service_request(
            ServiceRequestCreateRequest(
                client_id=document["client_id"],
                category_id=document["category_id"],
                title=document["title"],
                description=document["description"],
                country_code=document["country_code"],
                city=document["city"],
                coverage_zone=document["coverage_zone"],
                budget_amount=document.get("budget_amount"),
                requested_for=scheduled_date,
                attributes=document.get("attributes", {}),
            )
        )

        occurrence_document = await self._repository.create_occurrence(
            {
                "subscription_id": subscription_id,
                "request_id": service_request.request.id,
                "scheduled_date": scheduled_date,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        next_run = self._advance_date(self._parse_date_or_400(scheduled_date), document["frequency"])
        await self._repository.update_subscription(
            subscription_id, {"next_run_date": next_run.isoformat()}
        )
        document["next_run_date"] = next_run.isoformat()

        return GenerateOccurrenceResponse(
            module="recurring",
            subscription=await self._serialize_subscription(document),
            occurrence=self._serialize_occurrence(occurrence_document),
            matches_total=len(service_request.matches),
        )

    async def list_occurrences(self, subscription_id: str) -> OccurrenceListResponse:
        await self._get_subscription_document_or_404(subscription_id)
        documents = await self._repository.list_occurrences(subscription_id)
        return OccurrenceListResponse(
            module="recurring",
            subscription_id=subscription_id,
            total=len(documents),
            items=[self._serialize_occurrence(document) for document in documents],
        )

    @staticmethod
    def _today() -> date:
        return datetime.now(timezone.utc).date()

    @staticmethod
    def _parse_date_or_400(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date invalido, usa formato YYYY-MM-DD",
            ) from exc

    @staticmethod
    def _advance_date(current: date, frequency: str) -> date:
        if frequency == "weekly":
            return current + timedelta(days=7)
        if frequency == "biweekly":
            return current + timedelta(days=14)
        # monthly: avanza un mes calendario, ajustando fin de mes
        month = current.month + 1
        year = current.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        days_in_month = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                         31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
        return date(year, month, min(current.day, days_in_month))

    async def _get_subscription_document_or_404(self, subscription_id: str) -> dict:
        try:
            document = await self._repository.get_subscription_by_id(subscription_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="subscription_id invalido",
            ) from exc
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="suscripcion no encontrada",
            )
        return document

    async def _get_user_document_or_404(self, user_id: str) -> dict:
        try:
            document = await self._identity_repository.get_user_by_id(user_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id invalido",
            ) from exc
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user no encontrado",
            )
        return document

    async def _serialize_subscription(self, document: dict) -> SubscriptionSummary:
        occurrences_count = await self._repository.count_occurrences(str(document["_id"]))
        return SubscriptionSummary(
            id=str(document["_id"]),
            client_id=document["client_id"],
            category_id=document["category_id"],
            category_name=document["category_name"],
            title=document["title"],
            description=document["description"],
            pricing_mode=document["pricing_mode"],
            risk_level=document["risk_level"],
            country_code=document["country_code"],
            city=document["city"],
            coverage_zone=document["coverage_zone"],
            frequency=document["frequency"],
            budget_amount=document.get("budget_amount"),
            start_date=document["start_date"],
            next_run_date=document["next_run_date"],
            preferred_time=document.get("preferred_time"),
            attributes=document.get("attributes", {}),
            status=document["status"],
            occurrences_count=occurrences_count,
            created_at=str(document["_id"].generation_time.isoformat()),
        )

    def _serialize_occurrence(self, document: dict) -> OccurrenceSummary:
        return OccurrenceSummary(
            id=str(document["_id"]),
            subscription_id=document["subscription_id"],
            request_id=document["request_id"],
            scheduled_date=document["scheduled_date"],
            created_at=str(document["_id"].generation_time.isoformat()),
        )


recurring_service = RecurringService()

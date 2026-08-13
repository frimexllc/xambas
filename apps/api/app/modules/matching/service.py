from bson.errors import InvalidId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.modules.identity.repository import IdentityRepository
from app.modules.matching.repository import MatchingRepository
from app.modules.matching.seeds import LAUNCH_CATEGORY_DEFINITIONS
from app.modules.matching.schemas import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategorySummary,
    CategoryUpdateRequest,
    MatchListResponse,
    MatchSummary,
    MatchingStatusResponse,
    ServiceRequestCreateRequest,
    ServiceRequestListResponse,
    ServiceRequestResponse,
    ServiceRequestSummary,
)


class MatchingService:
    def __init__(self) -> None:
        self._repository = MatchingRepository()
        self._identity_repository = IdentityRepository()

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    async def ensure_launch_categories(self) -> None:
        for definition in LAUNCH_CATEGORY_DEFINITIONS:
            parent_document = await self._repository.upsert_category(
                name=definition["name"],
                parent_id=definition["parent_id"],
                attributes_schema=definition["attributes_schema"],
                pricing_mode=definition["pricing_mode"],
                risk_level=definition["risk_level"],
            )
            for child_name in definition["children"]:
                await self._repository.upsert_category(
                    name=child_name,
                    parent_id=str(parent_document["_id"]),
                    attributes_schema=definition["attributes_schema"],
                    pricing_mode=definition["pricing_mode"],
                    risk_level=definition["risk_level"],
                )

    def get_status(self) -> MatchingStatusResponse:
        return MatchingStatusResponse(
            module="matching",
            status="ready",
            collections=["categories", "service_requests", "matches"],
        )

    async def create_category(self, payload: CategoryCreateRequest) -> CategorySummary:
        if payload.parent_id is not None:
            await self._get_category_document_or_404(payload.parent_id)

        try:
            category_document = await self._repository.create_category(payload)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ya existe una categoria con ese nombre bajo el mismo parent_id",
            ) from exc
        return self._serialize_category(category_document)

    async def list_categories(self, parent_id: str | None = None) -> CategoryListResponse:
        if parent_id is not None:
            await self._get_category_document_or_404(parent_id)
        documents = await self._repository.list_categories(parent_id=parent_id)
        return CategoryListResponse(
            module="matching",
            total=len(documents),
            items=[self._serialize_category(document) for document in documents],
        )

    async def get_category(self, category_id: str) -> CategorySummary:
        document = await self._get_category_document_or_404(category_id)
        return self._serialize_category(document)

    async def update_category(self, category_id: str, payload: CategoryUpdateRequest) -> CategorySummary:
        await self._get_category_document_or_404(category_id)
        fields = {key: value for key, value in payload.model_dump().items() if value is not None}
        if fields:
            try:
                await self._repository.update_category(category_id, fields)
            except DuplicateKeyError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="ya existe una categoria con ese nombre bajo el mismo parent_id",
                ) from exc
        refreshed = await self._get_category_document_or_404(category_id)
        return self._serialize_category(refreshed)

    async def create_service_request(self, payload: ServiceRequestCreateRequest) -> ServiceRequestResponse:
        client_document = await self._get_user_document_or_404(payload.client_id)
        if client_document["role"] not in {"client", "both"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="solo un cliente puede crear service_requests",
            )

        category_document = await self._get_category_document_or_404(payload.category_id)
        service_request_document = await self._repository.create_service_request(
            payload,
            category_name=category_document["name"],
            pricing_mode=category_document["pricing_mode"],
            risk_level=category_document["risk_level"],
        )
        match_documents = await self._run_matching_for_request_document(service_request_document, category_document)
        return ServiceRequestResponse(
            module="matching",
            request=self._serialize_service_request(service_request_document),
            matches=[self._serialize_match(document) for document in match_documents],
        )

    async def list_service_requests(self, client_id: str | None = None) -> ServiceRequestListResponse:
        if client_id is not None:
            await self._get_user_document_or_404(client_id)
        documents = await self._repository.list_service_requests(client_id=client_id)
        return ServiceRequestListResponse(
            module="matching",
            total=len(documents),
            items=[self._serialize_service_request(document) for document in documents],
        )

    async def get_service_request(self, request_id: str) -> ServiceRequestResponse:
        request_document = await self._get_service_request_document_or_404(request_id)
        match_documents = await self._repository.list_matches_for_request(request_id)
        return ServiceRequestResponse(
            module="matching",
            request=self._serialize_service_request(request_document),
            matches=[self._serialize_match(document) for document in match_documents],
        )

    async def rerun_matching(self, request_id: str) -> MatchListResponse:
        request_document = await self._get_service_request_document_or_404(request_id)
        category_document = await self._get_category_document_or_404(request_document["category_id"])
        match_documents = await self._run_matching_for_request_document(request_document, category_document)
        return MatchListResponse(
            module="matching",
            request_id=request_id,
            total=len(match_documents),
            items=[self._serialize_match(document) for document in match_documents],
        )

    async def list_matches(self, request_id: str) -> MatchListResponse:
        await self._get_service_request_document_or_404(request_id)
        documents = await self._repository.list_matches_for_request(request_id)
        return MatchListResponse(
            module="matching",
            request_id=request_id,
            total=len(documents),
            items=[self._serialize_match(document) for document in documents],
        )

    async def list_matches_for_provider(self, provider_user_id: str) -> MatchListResponse:
        documents = await self._repository.list_matches_for_provider(provider_user_id)
        return MatchListResponse(
            module="matching",
            request_id="*",
            total=len(documents),
            items=[self._serialize_match(document) for document in documents],
        )

    async def accept_match(self, match_id: str, provider_user_id: str) -> MatchSummary:
        try:
            document = await self._repository.get_match_by_id(match_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="match_id invalido",
            ) from exc
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match no encontrado")
        if document["provider_user_id"] != provider_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="este match no pertenece al proveedor indicado",
            )
        await self._repository.update_match_status(match_id, "accepted")
        document["status"] = "accepted"
        return self._serialize_match(document)

    async def _get_category_document_or_404(self, category_id: str) -> dict:
        try:
            document = await self._repository.get_category_by_id(category_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="category_id invalido",
            ) from exc

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="categoria no encontrada",
            )
        return document

    async def _get_service_request_document_or_404(self, request_id: str) -> dict:
        try:
            document = await self._repository.get_service_request_by_id(request_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="request_id invalido",
            ) from exc

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="service_request no encontrado",
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

    async def _run_matching_for_request_document(
        self,
        request_document: dict,
        category_document: dict,
    ) -> list[dict]:
        category_ids = [str(category_document["_id"])]
        if category_document["parent_id"] is not None:
            category_ids.append(category_document["parent_id"])

        provider_profiles = await self._repository.list_provider_profiles_for_matching(
            category_ids=category_ids,
            coverage_zone=request_document["coverage_zone"],
        )

        match_documents: list[dict] = []
        for provider_profile in provider_profiles:
            score, reasons = self._score_provider_match(
                provider_profile=provider_profile,
                request_document=request_document,
                category_document=category_document,
            )
            if score <= 0:
                continue
            match_document = await self._repository.upsert_match(
                request_id=str(request_document["_id"]),
                provider_profile=provider_profile,
                score=score,
                reasons=reasons,
            )
            match_documents.append(match_document)

        next_status = "matched" if match_documents else "open"
        await self._repository.update_service_request_status(str(request_document["_id"]), next_status)
        request_document["status"] = next_status
        return sorted(match_documents, key=lambda item: (-item["score"], item["provider_business_name"]))

    def _score_provider_match(
        self,
        *,
        provider_profile: dict,
        request_document: dict,
        category_document: dict,
    ) -> tuple[int, list[str]]:
        reasons: list[str] = []

        if category_document["risk_level"] == "regulated" and not provider_profile["license_verified"]:
            return 0, ["categoria regulada sin licencia verificada"]

        score = 0
        selected_category_id = str(category_document["_id"])
        if selected_category_id in provider_profile["categories"]:
            score += 45
            reasons.append("coincidencia exacta de categoria")
        elif category_document["parent_id"] and category_document["parent_id"] in provider_profile["categories"]:
            score += 30
            reasons.append("coincidencia por categoria padre")
        else:
            return 0, ["sin cobertura de categoria"]

        if request_document["coverage_zone"] in provider_profile["coverage_zones"]:
            score += 25
            reasons.append("cobertura en la zona solicitada")

        rating_score = min(20, int(provider_profile["rating_avg"] * 4))
        if rating_score > 0:
            score += rating_score
            reasons.append("rating historico favorable")

        jobs_score = min(10, provider_profile["jobs_completed"])
        if jobs_score > 0:
            score += jobs_score
            reasons.append("experiencia previa en trabajos completados")

        if provider_profile["insurance_verified"]:
            score += 5
            reasons.append("seguro verificado")

        if provider_profile["license_verified"]:
            score += 5
            reasons.append("licencia verificada")

        return score, reasons

    def _serialize_category(self, document: dict) -> CategorySummary:
        return CategorySummary(
            id=str(document["_id"]),
            name=document["name"],
            parent_id=document["parent_id"],
            attributes_schema=document["attributes_schema"],
            pricing_mode=document["pricing_mode"],
            risk_level=document["risk_level"],
        )

    def _serialize_service_request(self, document: dict) -> ServiceRequestSummary:
        return ServiceRequestSummary(
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
            budget_amount=document["budget_amount"],
            requested_for=document["requested_for"],
            attributes=document["attributes"],
            status=document["status"],
            created_at=str(document["_id"].generation_time.isoformat()),
        )

    def _serialize_match(self, document: dict) -> MatchSummary:
        return MatchSummary(
            id=str(document["_id"]),
            request_id=document["request_id"],
            provider_profile_id=document["provider_profile_id"],
            provider_user_id=document["provider_user_id"],
            provider_business_name=document["provider_business_name"],
            provider_categories=document["provider_categories"],
            coverage_zones=document["coverage_zones"],
            score=document["score"],
            reasons=document["reasons"],
            status=document["status"],
            created_at=str(document["_id"].generation_time.isoformat()),
        )


matching_service = MatchingService()

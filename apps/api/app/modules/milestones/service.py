import asyncio
import uuid
from datetime import datetime, timezone

from bson.errors import InvalidId
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.storage import object_storage
from app.modules.identity.repository import IdentityRepository
from app.modules.matching.repository import MatchingRepository
from app.modules.milestones.repository import MilestonesRepository
from app.modules.milestones.schemas import (
    MilestoneStatusResponse,
    MilestoneSummary,
    MilestoneEvidence,
    PlanCreateRequest,
    PlanListResponse,
    PlanResponse,
    PlanSummary,
)

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_MAX_BYTES = 10 * 1024 * 1024


class MilestonesService:
    def __init__(self) -> None:
        self._repository = MilestonesRepository()
        self._matching_repository = MatchingRepository()
        self._identity_repository = IdentityRepository()

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    def get_status(self) -> MilestoneStatusResponse:
        return MilestoneStatusResponse(module="milestones", status="ready")

    async def create_plan(self, payload: PlanCreateRequest) -> PlanResponse:
        match = await self._get_match_or_404(payload.match_id)
        if match.get("status") != "accepted":
            raise HTTPException(status.HTTP_409_CONFLICT, "el match debe estar 'accepted'")
        request = await self._matching_repository.get_service_request_by_id(match["request_id"])
        if request is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "service_request no encontrado")
        if request["client_id"] != payload.client_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "client_id no coincide con la solicitud")
        if await self._repository.get_plan_by_match(payload.match_id) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "ya existe un plan por etapas para este match")

        milestones = [
            {
                "id": uuid.uuid4().hex,
                "title": item.title.strip(),
                "amount": round(item.amount, 2),
                "status": "pending",
                "evidence": [],
                "transfer_mode": None,
                "stripe_transfer_id": None,
                "submitted_at": None,
                "released_at": None,
            }
            for item in payload.milestones
        ]
        document = {
            "match_id": payload.match_id,
            "request_id": match["request_id"],
            "client_id": payload.client_id,
            "provider_user_id": match["provider_user_id"],
            "provider_profile_id": match["provider_profile_id"],
            "currency": payload.currency,
            "total_amount": round(sum(m["amount"] for m in milestones), 2),
            "released_amount": 0.0,
            "status": "active",
            "milestones": milestones,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        document = await self._repository.create_plan(document)
        return PlanResponse(module="milestones", plan=self._serialize_plan(document))

    async def submit_evidence(
        self, plan_id: str, milestone_id: str, *, provider_user_id: str, files: list[UploadFile]
    ) -> PlanResponse:
        document = await self._get_plan_or_404(plan_id)
        if document["provider_user_id"] != provider_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "este plan no pertenece al proveedor")
        milestone = self._find_milestone(document, milestone_id)
        if milestone["status"] == "released":
            raise HTTPException(status.HTTP_409_CONFLICT, "esta etapa ya fue liberada")
        if not files:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "sube al menos una foto de evidencia")

        for upload in files:
            if upload.content_type not in _ALLOWED_TYPES:
                raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "usa JPEG, PNG o WebP")
            content = await upload.read()
            if not content:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "archivo vacío")
            if len(content) > _MAX_BYTES:
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "cada foto máx 10 MB")
            path = f"{settings.storage_app_name}/milestones/{plan_id}/{milestone_id}/{uuid.uuid4().hex}.{_EXT[upload.content_type]}"
            stored = await asyncio.to_thread(object_storage.put_object, path, content, upload.content_type)
            milestone["evidence"].append({"path": stored["path"], "url": f"/api/milestones/files/{stored['path']}"})

        milestone["status"] = "submitted"
        milestone["submitted_at"] = datetime.now(timezone.utc).isoformat()
        await self._repository.update_plan(plan_id, {"milestones": document["milestones"]})
        return PlanResponse(module="milestones", plan=self._serialize_plan(document))

    async def approve_and_release(
        self, plan_id: str, milestone_id: str, *, client_id: str
    ) -> PlanResponse:
        document = await self._get_plan_or_404(plan_id)
        if document["client_id"] != client_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "solo el cliente puede liberar la etapa")
        milestone = self._find_milestone(document, milestone_id)
        if milestone["status"] != "submitted":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "la etapa debe tener evidencia enviada (submitted) para liberarse",
            )

        transfer_mode, transfer_id = await self._release_funds(document, milestone)
        milestone["status"] = "released"
        milestone["transfer_mode"] = transfer_mode
        milestone["stripe_transfer_id"] = transfer_id
        milestone["released_at"] = datetime.now(timezone.utc).isoformat()

        released_amount = round(
            sum(m["amount"] for m in document["milestones"] if m["status"] == "released"), 2
        )
        all_released = all(m["status"] == "released" for m in document["milestones"])
        document["released_amount"] = released_amount
        document["status"] = "completed" if all_released else document["status"]
        await self._repository.update_plan(
            plan_id,
            {
                "milestones": document["milestones"],
                "released_amount": released_amount,
                "status": document["status"],
            },
        )
        return PlanResponse(module="milestones", plan=self._serialize_plan(document))

    async def _release_funds(self, plan: dict, milestone: dict) -> tuple[str, str | None]:
        """Transferencia real vía Stripe Connect si está configurado; si no, modo manual."""
        provider = await self._identity_repository.get_provider_profile_by_id(plan["provider_profile_id"])
        connect_account = (provider or {}).get("stripe_connect_account_id")
        stripe_ready = bool(settings.stripe_secret_key) and settings.stripe_secret_key not in ("", "sk_test_replace_me")
        if not (connect_account and stripe_ready):
            return "manual", None
        # Ready para producción: cuando Stripe esté configurado y el proveedor tenga cuenta conectada.
        from app.modules.billing import stripe_client
        import stripe as stripe_sdk

        try:
            transfer = stripe_client.create_transfer(
                amount_cents=int(round(milestone["amount"] * 100)),
                currency=plan["currency"].lower(),
                destination_account_id=connect_account,
                metadata={"plan_id": str(plan["_id"]), "milestone_id": milestone["id"]},
            )
        except stripe_sdk.error.StripeError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Stripe rechazó la transferencia de la etapa: {exc.user_message or str(exc)}",
            ) from exc
        return "stripe", transfer.id

    async def list_plans(
        self, *, client_id: str | None, provider_user_id: str | None
    ) -> PlanListResponse:
        documents = await self._repository.list_plans(
            client_id=client_id, provider_user_id=provider_user_id
        )
        return PlanListResponse(
            module="milestones",
            total=len(documents),
            items=[self._serialize_plan(doc) for doc in documents],
        )

    async def get_plan(self, plan_id: str) -> PlanResponse:
        document = await self._get_plan_or_404(plan_id)
        return PlanResponse(module="milestones", plan=self._serialize_plan(document))

    async def get_file(self, path: str) -> tuple[bytes, str]:
        if not path.startswith(f"{settings.storage_app_name}/milestones/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "imagen no encontrada")
        try:
            return await asyncio.to_thread(object_storage.get_object, path)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_404_NOT_FOUND, "imagen no encontrada") from exc

    def _find_milestone(self, plan: dict, milestone_id: str) -> dict:
        for milestone in plan["milestones"]:
            if milestone["id"] == milestone_id:
                return milestone
        raise HTTPException(status.HTTP_404_NOT_FOUND, "etapa no encontrada")

    async def _get_match_or_404(self, match_id: str) -> dict:
        try:
            document = await self._matching_repository.get_match_by_id(match_id)
        except InvalidId as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "match_id inválido") from exc
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "match no encontrado")
        return document

    async def _get_plan_or_404(self, plan_id: str) -> dict:
        try:
            document = await self._repository.get_plan_by_id(plan_id)
        except InvalidId as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "plan_id inválido") from exc
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "plan no encontrado")
        return document

    def _serialize_plan(self, document: dict) -> PlanSummary:
        return PlanSummary(
            id=str(document["_id"]),
            match_id=document["match_id"],
            request_id=document["request_id"],
            client_id=document["client_id"],
            provider_user_id=document["provider_user_id"],
            provider_profile_id=document["provider_profile_id"],
            currency=document["currency"],
            total_amount=document["total_amount"],
            released_amount=document.get("released_amount", 0.0),
            status=document["status"],
            milestones=[
                MilestoneSummary(
                    id=m["id"],
                    title=m["title"],
                    amount=m["amount"],
                    status=m["status"],
                    evidence=[MilestoneEvidence(**e) for e in m.get("evidence", [])],
                    transfer_mode=m.get("transfer_mode"),
                    stripe_transfer_id=m.get("stripe_transfer_id"),
                    submitted_at=m.get("submitted_at"),
                    released_at=m.get("released_at"),
                )
                for m in document["milestones"]
            ],
            created_at=document["created_at"],
        )


milestones_service = MilestonesService()

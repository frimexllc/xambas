from datetime import datetime, timezone

from bson.errors import InvalidId
from fastapi import HTTPException, status

import stripe as stripe_sdk

from app.core.config import settings
from app.modules.billing import stripe_client, tiers
from app.modules.billing.payments_repository import PaymentsRepository
from app.modules.billing.schemas import (
    ConnectOnboardingResponse,
    ConnectStatusResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListResponse,
    PaymentSummary,
)
from app.modules.identity.repository import IdentityRepository
from app.modules.matching.repository import MatchingRepository


def _to_minor_units(amount: float) -> int:
    return int(round(amount * 100))


class PaymentsService:
    def __init__(self) -> None:
        self._repository = PaymentsRepository()
        self._matching_repository = MatchingRepository()
        self._identity_repository = IdentityRepository()

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    # ------------------------------------------------------------------
    # Creacion del pago (deposito completo, retenido en custodia)
    # ------------------------------------------------------------------

    async def create_payment(self, payload: PaymentCreateRequest) -> PaymentCreateResponse:
        match_document = await self._get_match_or_404(payload.match_id)
        if match_document.get("status") != "accepted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="el match debe estar 'accepted' antes de poder pagarse",
            )

        request_document = await self._matching_repository.get_service_request_by_id(
            match_document["request_id"]
        )
        if request_document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service_request no encontrado")
        if request_document["client_id"] != payload.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="client_id no coincide con el cliente de esta solicitud",
            )

        existing = await self._repository.get_active_payment_for_match(payload.match_id)
        if existing is not None:
            client_secret = None
            if existing["status"] == "pending" and existing.get("stripe_payment_intent_id"):
                intent = stripe_client.retrieve_payment_intent(existing["stripe_payment_intent_id"])
                client_secret = intent.client_secret
            return PaymentCreateResponse(
                module="billing",
                payment=self._serialize_payment(existing),
                client_secret=client_secret,
                publishable_key=settings.stripe_publishable_key or None,
            )

        provider_document = await self._identity_repository.get_provider_profile_by_id(
            match_document["provider_profile_id"]
        )
        if provider_document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="provider_profile no encontrado")

        quote = tiers.compute_commission_quote(
            job_amount=payload.job_amount,
            jobs_completed=provider_document.get("jobs_completed", 0),
            rating_avg=provider_document.get("rating_avg", 0.0),
            cancellation_rate_pct=provider_document.get("cancellation_rate", 0.0),
        )

        document = await self._repository.create_payment(
            {
                "match_id": payload.match_id,
                "request_id": match_document["request_id"],
                "client_id": payload.client_id,
                "provider_user_id": match_document["provider_user_id"],
                "provider_profile_id": match_document["provider_profile_id"],
                "job_amount": payload.job_amount,
                "currency": settings.default_currency,
                "status": "pending",
                "stripe_payment_intent_id": None,
                "stripe_transfer_id": None,
                **quote,
            }
        )
        payment_id = str(document["_id"])

        try:
            intent = stripe_client.create_payment_intent(
                amount_cents=_to_minor_units(quote["client_total"]),
                currency=settings.default_currency,
                metadata={
                    "payment_id": payment_id,
                    "match_id": payload.match_id,
                    "request_id": match_document["request_id"],
                },
            )
        except stripe_sdk.error.StripeError as exc:
            await self._repository.update_fields(payment_id, {"status": "failed"})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe rechazo la creacion del pago: {exc.user_message or str(exc)}",
            ) from exc

        await self._repository.update_fields(payment_id, {"stripe_payment_intent_id": intent.id})
        document["stripe_payment_intent_id"] = intent.id

        return PaymentCreateResponse(
            module="billing",
            payment=self._serialize_payment(document),
            client_secret=intent.client_secret,
            publishable_key=settings.stripe_publishable_key or None,
        )

    # ------------------------------------------------------------------
    # Sincronizacion / consulta
    # ------------------------------------------------------------------

    async def get_payment(self, payment_id: str, *, sync: bool = True) -> PaymentSummary:
        document = await self._get_payment_or_404(payment_id)
        if sync and document["status"] == "pending" and document.get("stripe_payment_intent_id"):
            document = await self._sync_from_stripe(document)
        return self._serialize_payment(document)

    async def _sync_from_stripe(self, document: dict) -> dict:
        try:
            intent = stripe_client.retrieve_payment_intent(document["stripe_payment_intent_id"])
        except stripe_sdk.error.StripeError:
            return document

        new_status = _map_stripe_status(intent.status, current=document["status"])
        if new_status != document["status"]:
            await self._repository.update_fields(str(document["_id"]), {"status": new_status})
            document["status"] = new_status
        return document

    async def list_payments(
        self, *, client_id: str | None, provider_user_id: str | None, admin: bool
    ) -> PaymentListResponse:
        if admin:
            documents = await self._repository.list_all()
        elif client_id:
            documents = await self._repository.list_for_client(client_id)
        elif provider_user_id:
            documents = await self._repository.list_for_provider(provider_user_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="se requiere client_id o provider_user_id",
            )
        return PaymentListResponse(
            module="billing",
            total=len(documents),
            items=[self._serialize_payment(doc) for doc in documents],
        )

    # ------------------------------------------------------------------
    # Webhook de Stripe (fuente de verdad en produccion)
    # ------------------------------------------------------------------

    async def handle_stripe_webhook(self, payload: bytes, sig_header: str) -> dict:
        if not settings.stripe_webhook_secret or settings.stripe_webhook_secret == "whsec_replace_me":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="STRIPE_WEBHOOK_SECRET no esta configurado",
            )
        try:
            event = stripe_client.construct_webhook_event(
                payload=payload, sig_header=sig_header, webhook_secret=settings.stripe_webhook_secret
            )
        except (ValueError, stripe_sdk.error.SignatureVerificationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="firma de webhook invalida"
            ) from exc

        event_object = event["data"]["object"]
        event_type = event["type"]

        if event_type in ("payment_intent.succeeded", "payment_intent.payment_failed", "payment_intent.canceled"):
            payment_intent_id = event_object["id"]
            document = await self._get_payment_by_stripe_intent(payment_intent_id)
            if document is not None:
                new_status = _map_stripe_status(event_object["status"], current=document["status"])
                if new_status != document["status"]:
                    await self._repository.update_fields(str(document["_id"]), {"status": new_status})

        return {"received": True, "type": event_type}

    async def _get_payment_by_stripe_intent(self, payment_intent_id: str) -> dict | None:
        for document in await self._repository.list_all():
            if document.get("stripe_payment_intent_id") == payment_intent_id:
                return document
        return None

    # ------------------------------------------------------------------
    # Confirmacion de finalizacion -> liberacion de fondos al proveedor
    # ------------------------------------------------------------------

    async def confirm_completion_and_release(self, payment_id: str, actor_client_id: str) -> PaymentSummary:
        document = await self._get_payment_or_404(payment_id)
        if document["client_id"] != actor_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="solo el cliente que pago puede confirmar la finalizacion",
            )

        if document["status"] == "pending":
            document = await self._sync_from_stripe(document)

        if document["status"] != "held_in_escrow":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"el pago debe estar 'held_in_escrow' para liberarse (estado actual: {document['status']})",
            )

        provider_document = await self._identity_repository.get_provider_profile_by_id(
            document["provider_profile_id"]
        )
        connect_account_id = (provider_document or {}).get("stripe_connect_account_id")
        if not connect_account_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="el proveedor no ha completado el onboarding de pagos (Stripe Connect)",
            )

        try:
            transfer = stripe_client.create_transfer(
                amount_cents=_to_minor_units(document["provider_receives"]),
                currency=document["currency"],
                destination_account_id=connect_account_id,
                metadata={"payment_id": payment_id, "match_id": document["match_id"]},
            )
        except stripe_sdk.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe rechazo la transferencia al proveedor: {exc.user_message or str(exc)}",
            ) from exc

        await self._repository.update_fields(
            payment_id,
            {
                "status": "released",
                "stripe_transfer_id": transfer.id,
                "released_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        document["status"] = "released"
        document["stripe_transfer_id"] = transfer.id
        return self._serialize_payment(document)

    # ------------------------------------------------------------------
    # Reembolsos
    # ------------------------------------------------------------------

    async def refund_payment(self, payment_id: str, reason: str | None) -> PaymentSummary:
        document = await self._get_payment_or_404(payment_id)
        if document["status"] not in ("pending", "held_in_escrow"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "solo se pueden reembolsar pagos 'pending' o 'held_in_escrow'; "
                    "un pago ya 'released' requiere un proceso de reversal aparte"
                ),
            )
        if not document.get("stripe_payment_intent_id"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="este pago no tiene un cargo real que reembolsar"
            )

        try:
            stripe_client.create_refund(payment_intent_id=document["stripe_payment_intent_id"], reason=reason)
        except stripe_sdk.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe rechazo el reembolso: {exc.user_message or str(exc)}",
            ) from exc

        await self._repository.update_fields(payment_id, {"status": "refunded"})
        document["status"] = "refunded"
        return self._serialize_payment(document)

    # ------------------------------------------------------------------
    # Stripe Connect: onboarding del proveedor
    # ------------------------------------------------------------------

    async def create_connect_onboarding(
        self, provider_profile_id: str, *, refresh_url: str, return_url: str
    ) -> ConnectOnboardingResponse:
        provider_document = await self._get_provider_profile_or_404(provider_profile_id)
        account_id = provider_document.get("stripe_connect_account_id")

        if not account_id:
            user_document = await self._identity_repository.get_user_by_id(provider_document["user_id"])
            if user_document is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="usuario del proveedor no encontrado")
            try:
                account = stripe_client.create_connected_account(
                    email=user_document["email"], country=settings.default_country_code
                )
            except stripe_sdk.error.StripeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Stripe rechazo la creacion de la cuenta conectada: {exc.user_message or str(exc)}",
                ) from exc
            account_id = account.id
            await self._identity_repository.update_provider_profile_fields(
                provider_profile_id, {"stripe_connect_account_id": account_id}
            )

        try:
            link = stripe_client.create_account_link(
                account_id=account_id, refresh_url=refresh_url, return_url=return_url
            )
        except stripe_sdk.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe rechazo la creacion del enlace de onboarding: {exc.user_message or str(exc)}",
            ) from exc

        return ConnectOnboardingResponse(
            module="billing",
            provider_profile_id=provider_profile_id,
            stripe_connect_account_id=account_id,
            onboarding_url=link.url,
        )

    async def get_connect_status(self, provider_profile_id: str) -> ConnectStatusResponse:
        provider_document = await self._get_provider_profile_or_404(provider_profile_id)
        account_id = provider_document.get("stripe_connect_account_id")
        if not account_id:
            return ConnectStatusResponse(
                module="billing",
                provider_profile_id=provider_profile_id,
                stripe_connect_account_id=None,
                charges_enabled=False,
                payouts_enabled=False,
                details_submitted=False,
            )
        try:
            account = stripe_client.retrieve_connected_account(account_id)
        except stripe_sdk.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe rechazo la consulta de la cuenta: {exc.user_message or str(exc)}",
            ) from exc
        return ConnectStatusResponse(
            module="billing",
            provider_profile_id=provider_profile_id,
            stripe_connect_account_id=account_id,
            charges_enabled=account.charges_enabled,
            payouts_enabled=account.payouts_enabled,
            details_submitted=account.details_submitted,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_match_or_404(self, match_id: str) -> dict:
        try:
            document = await self._matching_repository.get_match_by_id(match_id)
        except InvalidId as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="match_id invalido") from exc
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match no encontrado")
        return document

    async def _get_provider_profile_or_404(self, provider_profile_id: str) -> dict:
        try:
            document = await self._identity_repository.get_provider_profile_by_id(provider_profile_id)
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="provider_profile_id invalido"
            ) from exc
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="provider_profile no encontrado")
        return document

    async def _get_payment_or_404(self, payment_id: str) -> dict:
        try:
            document = await self._repository.get_by_id(payment_id)
        except InvalidId as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_id invalido") from exc
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pago no encontrado")
        return document

    def _serialize_payment(self, document: dict) -> PaymentSummary:
        return PaymentSummary(
            id=str(document["_id"]),
            match_id=document["match_id"],
            request_id=document["request_id"],
            client_id=document["client_id"],
            provider_user_id=document["provider_user_id"],
            provider_profile_id=document["provider_profile_id"],
            job_amount=document["job_amount"],
            provider_tier=document["provider_tier"],
            provider_commission_pct=document["provider_commission_pct"],
            provider_commission_amount=document["provider_commission_amount"],
            client_fee_amount=document["client_fee_amount"],
            client_total=document["client_total"],
            provider_receives=document["provider_receives"],
            platform_revenue=document["platform_revenue"],
            currency=document["currency"],
            status=document["status"],
            stripe_payment_intent_id=document.get("stripe_payment_intent_id"),
            stripe_transfer_id=document.get("stripe_transfer_id"),
            created_at=document["created_at"],
            updated_at=document.get("updated_at"),
            released_at=document.get("released_at"),
        )


def _map_stripe_status(stripe_status: str, *, current: str) -> str:
    if stripe_status == "succeeded":
        return "held_in_escrow" if current not in ("released", "refunded") else current
    if stripe_status in ("canceled",):
        return "cancelled"
    if stripe_status in ("requires_payment_method",) and current == "pending":
        return "pending"
    return current


payments_service = PaymentsService()

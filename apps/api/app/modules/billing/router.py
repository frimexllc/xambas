from fastapi import APIRouter, Depends, Header, Query, Request

from app.core.config import settings
from app.modules.admin.router import require_admin
from app.modules.admin.schemas import AdminSummary
from app.modules.identity.dependencies import get_current_user, require_client, require_provider
from app.modules.identity.schemas import UserSummary
from app.modules.billing.payments_service import payments_service
from app.modules.billing.schemas import (
    BillingStatusResponse,
    CommissionQuoteResponse,
    ConnectOnboardingRequest,
    ConnectOnboardingResponse,
    ConnectStatusResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListResponse,
    PaymentProviderConfig,
    PaymentSummary,
    ProviderTierListResponse,
    RefundRequest,
)
from app.modules.billing.service import billing_gateway_resolver

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/status")
def billing_status() -> BillingStatusResponse:
    return billing_gateway_resolver.get_status()


@router.get("/provider")
def billing_provider(
    country_code: str | None = Query(default=None, min_length=2, max_length=2),
) -> PaymentProviderConfig:
    return billing_gateway_resolver.get_provider_config(country_code=country_code)


@router.get("/tiers")
def billing_tiers() -> ProviderTierListResponse:
    return billing_gateway_resolver.get_tiers()


@router.get("/commission/quote")
async def billing_commission_quote(
    provider_profile_id: str = Query(...),
    job_amount: float = Query(..., gt=0),
) -> CommissionQuoteResponse:
    return await billing_gateway_resolver.quote_commission(provider_profile_id, job_amount)


# ---------------------------------------------------------------------------
# Pagos en custodia
# ---------------------------------------------------------------------------


@router.post("/payments")
async def create_payment(
    payload: PaymentCreateRequest,
    current_user: UserSummary = Depends(require_client),
) -> PaymentCreateResponse:
    payload = payload.model_copy(update={"client_id": current_user.id})
    return await payments_service.create_payment(payload)


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> PaymentSummary:
    return await payments_service.get_payment(payment_id, acting_user_id=current_user.id)


@router.get("/payments")
async def list_payments(
    current_user: UserSummary = Depends(get_current_user),
) -> PaymentListResponse:
    # "Mis pagos": como cliente o como proveedor, según el rol de la cuenta.
    if current_user.role == "provider":
        return await payments_service.list_payments(
            client_id=None, provider_user_id=current_user.id, admin=False
        )
    return await payments_service.list_payments(
        client_id=current_user.id, provider_user_id=None, admin=False
    )


@router.post("/payments/{payment_id}/confirm-completion")
async def confirm_completion(
    payment_id: str,
    current_user: UserSummary = Depends(require_client),
) -> PaymentSummary:
    return await payments_service.confirm_completion_and_release(payment_id, current_user.id)


@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: str, payload: RefundRequest, _: AdminSummary = Depends(require_admin)
) -> PaymentSummary:
    return await payments_service.refund_payment(payment_id, payload.reason)


@router.get("/admin/payments")
async def admin_list_payments(_: AdminSummary = Depends(require_admin)) -> PaymentListResponse:
    return await payments_service.list_payments(client_id=None, provider_user_id=None, admin=True)


# ---------------------------------------------------------------------------
# Stripe Connect (onboarding del proveedor)
# ---------------------------------------------------------------------------


@router.post("/connect/onboarding-link")
async def create_connect_onboarding(
    payload: ConnectOnboardingRequest,
    current_user: UserSummary = Depends(require_provider),
) -> ConnectOnboardingResponse:
    base = settings.provider_app_url.rstrip("/")
    return await payments_service.create_connect_onboarding(
        payload.provider_profile_id,
        refresh_url=f"{base}/connect/refresh",
        return_url=f"{base}/connect/return",
        acting_user_id=current_user.id,
    )


@router.get("/connect/status")
async def get_connect_status(
    provider_profile_id: str = Query(...),
    current_user: UserSummary = Depends(require_provider),
) -> ConnectStatusResponse:
    return await payments_service.get_connect_status(
        provider_profile_id, acting_user_id=current_user.id
    )


# ---------------------------------------------------------------------------
# Webhook de Stripe
# ---------------------------------------------------------------------------


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(alias="stripe-signature")) -> dict:
    payload = await request.body()
    return await payments_service.handle_stripe_webhook(payload, stripe_signature)

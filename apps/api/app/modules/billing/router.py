from fastapi import APIRouter, Query

from app.modules.billing.schemas import BillingStatusResponse, PaymentProviderConfig
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

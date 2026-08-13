from bson.errors import InvalidId
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.billing import tiers
from app.modules.billing.gateways.base import PaymentGateway
from app.modules.billing.gateways.mercadopago_gateway import MercadoPagoGateway
from app.modules.billing.gateways.stripe_gateway import StripeGateway
from app.modules.billing.schemas import (
    BillingStatusResponse,
    CommissionQuoteResponse,
    PaymentProviderConfig,
    ProviderTierListResponse,
)
from app.modules.identity.repository import IdentityRepository


class BillingGatewayResolver:
    def __init__(self) -> None:
        self._gateways: dict[str, PaymentGateway] = {
            "stripe": StripeGateway(),
            "mercado_pago": MercadoPagoGateway(),
        }
        self._identity_repository = IdentityRepository()

    def list_supported_providers(self) -> list[str]:
        return list(self._gateways.keys())

    def resolve(self, country_code: str | None = None) -> PaymentGateway:
        if settings.payments_provider in self._gateways:
            return self._gateways[settings.payments_provider]

        normalized_country = (country_code or settings.default_country_code).upper()
        if normalized_country == "US":
            return self._gateways["stripe"]
        if normalized_country == "MX":
            return self._gateways["mercado_pago"]

        return self._gateways["stripe"]

    def get_provider_config(self, country_code: str | None = None) -> PaymentProviderConfig:
        return self.resolve(country_code=country_code).get_config()

    def get_status(self) -> BillingStatusResponse:
        return BillingStatusResponse(
            module="billing",
            status="ready",
            strategy=settings.payments_provider,
            default_country_code=settings.default_country_code,
            supported_providers=self.list_supported_providers(),
        )

    def get_tiers(self) -> ProviderTierListResponse:
        return ProviderTierListResponse(
            module="billing",
            client_fee_pct=tiers.CLIENT_FEE_PCT,
            client_fee_min=tiers.CLIENT_FEE_MIN,
            client_fee_cap=tiers.CLIENT_FEE_CAP,
            tiers=tiers.list_tiers(),
        )

    async def quote_commission(
        self, provider_profile_id: str, job_amount: float
    ) -> CommissionQuoteResponse:
        if job_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="job_amount debe ser mayor a 0"
            )
        try:
            provider_document = await self._identity_repository.get_provider_profile_by_id(
                provider_profile_id
            )
        except InvalidId as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="provider_profile_id invalido"
            ) from exc
        if provider_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="provider_profile no encontrado"
            )

        quote = tiers.compute_commission_quote(
            job_amount=job_amount,
            jobs_completed=provider_document.get("jobs_completed", 0),
            rating_avg=provider_document.get("rating_avg", 0.0),
            cancellation_rate_pct=provider_document.get("cancellation_rate", 0.0),
        )
        return CommissionQuoteResponse(module="billing", job_amount=job_amount, **quote)


billing_gateway_resolver = BillingGatewayResolver()

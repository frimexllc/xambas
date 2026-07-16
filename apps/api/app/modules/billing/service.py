from app.core.config import settings
from app.modules.billing.gateways.base import PaymentGateway
from app.modules.billing.gateways.mercadopago_gateway import MercadoPagoGateway
from app.modules.billing.gateways.stripe_gateway import StripeGateway
from app.modules.billing.schemas import BillingStatusResponse, PaymentProviderConfig


class BillingGatewayResolver:
    def __init__(self) -> None:
        self._gateways: dict[str, PaymentGateway] = {
            "stripe": StripeGateway(),
            "mercado_pago": MercadoPagoGateway(),
        }

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


billing_gateway_resolver = BillingGatewayResolver()

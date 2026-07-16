from app.core.config import settings
from app.modules.billing.gateways.base import PaymentGateway
from app.modules.billing.schemas import PaymentProviderConfig


class MercadoPagoGateway(PaymentGateway):
    provider_name = "mercado_pago"

    def get_config(self) -> PaymentProviderConfig:
        return PaymentProviderConfig(
            provider="mercado_pago",
            country_code="MX",
            environment=settings.app_env,
            supports_escrow=True,
            supports_connected_accounts=True,
            webhook_mode="shared_secret",
        )

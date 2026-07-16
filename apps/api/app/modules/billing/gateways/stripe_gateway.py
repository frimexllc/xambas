from app.core.config import settings
from app.modules.billing.gateways.base import PaymentGateway
from app.modules.billing.schemas import PaymentProviderConfig


class StripeGateway(PaymentGateway):
    provider_name = "stripe"

    def get_config(self) -> PaymentProviderConfig:
        return PaymentProviderConfig(
            provider="stripe",
            country_code="US",
            environment=settings.app_env,
            supports_escrow=True,
            supports_connected_accounts=True,
            webhook_mode="signature_secret",
        )

from typing import Literal

from pydantic import BaseModel


PaymentProviderName = Literal["stripe", "mercado_pago"]


class PaymentProviderConfig(BaseModel):
    provider: PaymentProviderName
    country_code: str
    environment: str
    supports_escrow: bool
    supports_connected_accounts: bool
    webhook_mode: str


class BillingStatusResponse(BaseModel):
    module: str
    status: str
    strategy: str
    default_country_code: str
    supported_providers: list[PaymentProviderName]

from typing import Literal

from pydantic import BaseModel


PaymentProviderName = Literal["stripe", "mercado_pago"]
ProviderTierName = Literal["nuevo", "plata", "oro", "platino"]


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


class ProviderTierInfo(BaseModel):
    tier: ProviderTierName
    commission_rate_pct: float
    requirements: str


class ProviderTierListResponse(BaseModel):
    module: str
    client_fee_pct: float
    client_fee_min: float
    client_fee_cap: float
    tiers: list[ProviderTierInfo]


class CommissionQuoteResponse(BaseModel):
    module: str
    job_amount: float
    provider_tier: ProviderTierName
    provider_commission_pct: float
    provider_commission_amount: float
    client_fee_amount: float
    client_total: float
    provider_receives: float
    platform_revenue: float


PaymentStatus = Literal["pending", "held_in_escrow", "released", "refunded", "failed", "cancelled"]


class PaymentCreateRequest(BaseModel):
    match_id: str
    client_id: str
    job_amount: float


class PaymentSummary(BaseModel):
    id: str
    match_id: str
    request_id: str
    client_id: str
    provider_user_id: str
    provider_profile_id: str
    job_amount: float
    provider_tier: ProviderTierName
    provider_commission_pct: float
    provider_commission_amount: float
    client_fee_amount: float
    client_total: float
    provider_receives: float
    platform_revenue: float
    currency: str
    status: PaymentStatus
    stripe_payment_intent_id: str | None = None
    stripe_transfer_id: str | None = None
    created_at: str
    updated_at: str | None = None
    released_at: str | None = None


class PaymentCreateResponse(BaseModel):
    module: str
    payment: PaymentSummary
    client_secret: str | None = None
    publishable_key: str | None = None


class PaymentListResponse(BaseModel):
    module: str
    total: int
    items: list[PaymentSummary]


class RefundRequest(BaseModel):
    reason: str | None = None


class ConnectOnboardingRequest(BaseModel):
    provider_profile_id: str


class ConnectOnboardingResponse(BaseModel):
    module: str
    provider_profile_id: str
    stripe_connect_account_id: str
    onboarding_url: str


class ConnectStatusResponse(BaseModel):
    module: str
    provider_profile_id: str
    stripe_connect_account_id: str | None
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool

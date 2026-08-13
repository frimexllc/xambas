from typing import Literal

from pydantic import BaseModel, Field


UserRole = Literal["client", "provider", "both"]
KycStatus = Literal["pending", "in_review", "verified", "rejected"]


class ProviderProfileDraft(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    categories: list[str] = Field(default_factory=list)
    coverage_zones: list[str] = Field(default_factory=list)
    insurance_verified: bool = False
    license_verified: bool = False


class UserBootstrapRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    phone: str = Field(min_length=7, max_length=25)
    role: UserRole
    locale: str = "es-MX"
    provider_profile: ProviderProfileDraft | None = None


class UserSummary(BaseModel):
    id: str
    role: UserRole
    email: str
    phone: str
    auth_provider: str
    locale: str
    phone_verified: bool
    kyc_status: KycStatus
    is_active: bool = True
    created_at: str


class ProviderProfileSummary(BaseModel):
    id: str
    user_id: str
    business_name: str
    categories: list[str]
    coverage_zones: list[str]
    tier: str
    rating_avg: float
    jobs_completed: int
    cancellation_rate: float
    insurance_verified: bool
    license_verified: bool
    portfolio_media: list[str]
    stripe_connect_account_id: str | None = None
    mercadopago_account_id: str | None = None
    is_active: bool = True


class UserListResponse(BaseModel):
    module: str
    total: int
    items: list[UserSummary]


class UserAdminUpdateRequest(BaseModel):
    role: UserRole | None = None
    kyc_status: KycStatus | None = None
    is_active: bool | None = None


class ProviderProfileListResponse(BaseModel):
    module: str
    total: int
    items: list[ProviderProfileSummary]


class ProviderProfileAdminUpdateRequest(BaseModel):
    tier: str | None = None
    insurance_verified: bool | None = None
    license_verified: bool | None = None
    is_active: bool | None = None


class IdentityStatusResponse(BaseModel):
    module: str
    status: str
    supported_roles: list[UserRole]
    supported_kyc_statuses: list[KycStatus]


class UserBootstrapResponse(BaseModel):
    module: str
    status: str
    user: UserSummary
    provider_profile: ProviderProfileSummary | None = None
    next_steps: list[str]


class IdentityUserResponse(BaseModel):
    module: str
    user: UserSummary
    provider_profile: ProviderProfileSummary | None = None


class OtpRequestPayload(BaseModel):
    user_id: str
    purpose: Literal["registration", "login"] = "registration"
    channel: Literal["sms"] = "sms"


class OtpRequestResponse(BaseModel):
    module: str
    status: str
    challenge_id: str
    expires_at: str
    delivery_target: str
    debug_code: str | None = None


class OtpVerifyPayload(BaseModel):
    user_id: str
    challenge_id: str
    code: str = Field(min_length=4, max_length=10)
    device_name: str = Field(default="unknown-device", min_length=2, max_length=120)


class SessionSummary(BaseModel):
    session_id: str
    token: str
    expires_at: str
    user_id: str
    device_name: str


class OtpVerifyResponse(BaseModel):
    module: str
    status: str
    user: UserSummary
    session: SessionSummary

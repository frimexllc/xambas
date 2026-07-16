from typing import Any, Literal

from pydantic import BaseModel, Field


PricingMode = Literal["fixed", "quote", "both"]
RiskLevel = Literal["standard", "regulated"]
ServiceRequestStatus = Literal["open", "matched", "closed", "cancelled"]
MatchStatus = Literal["suggested", "accepted", "rejected", "expired"]


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    parent_id: str | None = None
    attributes_schema: dict[str, Any] = Field(default_factory=dict)
    pricing_mode: PricingMode = "quote"
    risk_level: RiskLevel = "standard"


class CategorySummary(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    attributes_schema: dict[str, Any]
    pricing_mode: PricingMode
    risk_level: RiskLevel


class MatchingStatusResponse(BaseModel):
    module: str
    status: str
    collections: list[str]


class CategoryListResponse(BaseModel):
    module: str
    total: int
    items: list[CategorySummary]


class ServiceRequestCreateRequest(BaseModel):
    client_id: str
    category_id: str
    title: str = Field(min_length=4, max_length=140)
    description: str = Field(min_length=10, max_length=2000)
    country_code: str = Field(min_length=2, max_length=4)
    city: str = Field(min_length=2, max_length=80)
    coverage_zone: str = Field(min_length=2, max_length=120)
    budget_amount: float | None = Field(default=None, ge=0)
    requested_for: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ServiceRequestSummary(BaseModel):
    id: str
    client_id: str
    category_id: str
    category_name: str
    title: str
    description: str
    pricing_mode: PricingMode
    risk_level: RiskLevel
    country_code: str
    city: str
    coverage_zone: str
    budget_amount: float | None = None
    requested_for: str | None = None
    attributes: dict[str, Any]
    status: ServiceRequestStatus
    created_at: str


class MatchSummary(BaseModel):
    id: str
    request_id: str
    provider_profile_id: str
    provider_user_id: str
    provider_business_name: str
    provider_categories: list[str]
    coverage_zones: list[str]
    score: int
    reasons: list[str]
    status: MatchStatus
    created_at: str


class ServiceRequestResponse(BaseModel):
    module: str
    request: ServiceRequestSummary
    matches: list[MatchSummary]


class ServiceRequestListResponse(BaseModel):
    module: str
    total: int
    items: list[ServiceRequestSummary]


class MatchListResponse(BaseModel):
    module: str
    request_id: str
    total: int
    items: list[MatchSummary]

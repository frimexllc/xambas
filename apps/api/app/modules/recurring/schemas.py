from typing import Any, Literal

from pydantic import BaseModel, Field


Frequency = Literal["weekly", "biweekly", "monthly"]
SubscriptionStatus = Literal["active", "paused", "cancelled"]


class SubscriptionCreateRequest(BaseModel):
    client_id: str
    category_id: str
    title: str = Field(min_length=4, max_length=140)
    description: str = Field(min_length=10, max_length=2000)
    country_code: str = Field(min_length=2, max_length=4)
    city: str = Field(min_length=2, max_length=80)
    coverage_zone: str = Field(min_length=2, max_length=120)
    frequency: Frequency
    budget_amount: float | None = Field(default=None, ge=0)
    start_date: str | None = Field(default=None, description="YYYY-MM-DD; por defecto hoy")
    preferred_time: str | None = Field(default=None, max_length=40)
    attributes: dict[str, Any] = Field(default_factory=dict)


class SubscriptionSummary(BaseModel):
    id: str
    client_id: str
    category_id: str
    category_name: str
    title: str
    description: str
    pricing_mode: str
    risk_level: str
    country_code: str
    city: str
    coverage_zone: str
    frequency: Frequency
    budget_amount: float | None = None
    start_date: str
    next_run_date: str
    preferred_time: str | None = None
    attributes: dict[str, Any]
    status: SubscriptionStatus
    occurrences_count: int
    created_at: str


class OccurrenceSummary(BaseModel):
    id: str
    subscription_id: str
    request_id: str
    scheduled_date: str
    created_at: str


class RecurringStatusResponse(BaseModel):
    module: str
    status: str
    collections: list[str]
    supported_frequencies: list[str]


class SubscriptionResponse(BaseModel):
    module: str
    subscription: SubscriptionSummary


class SubscriptionListResponse(BaseModel):
    module: str
    total: int
    items: list[SubscriptionSummary]


class OccurrenceListResponse(BaseModel):
    module: str
    subscription_id: str
    total: int
    items: list[OccurrenceSummary]


class GenerateOccurrenceResponse(BaseModel):
    module: str
    subscription: SubscriptionSummary
    occurrence: OccurrenceSummary
    matches_total: int

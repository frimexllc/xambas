from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    tier: str
    commission_pct: float
    rating_avg: float
    jobs_completed: int
    active_opportunities: int
    accepted_jobs: int
    earnings_released: float
    earnings_in_escrow: float


class RecurringVisit(BaseModel):
    subscription_id: str
    title: str
    frequency: str
    scheduled_date: str
    request_id: str
    match_id: str
    match_status: str


class ProviderDashboardResponse(BaseModel):
    module: str
    provider_user_id: str
    metrics: DashboardMetrics
    recurring_visits: list[RecurringVisit]

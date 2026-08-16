from typing import Literal

from pydantic import BaseModel, Field

MilestoneStatus = Literal["pending", "submitted", "released"]
PlanStatus = Literal["active", "completed", "cancelled"]
TransferMode = Literal["stripe", "manual"]


class MilestoneInput(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    amount: float = Field(gt=0)


class PlanCreateRequest(BaseModel):
    match_id: str
    client_id: str
    currency: str = "MXN"
    milestones: list[MilestoneInput] = Field(min_length=1, max_length=12)


class MilestoneEvidence(BaseModel):
    path: str
    url: str


class MilestoneSummary(BaseModel):
    id: str
    title: str
    amount: float
    status: MilestoneStatus
    evidence: list[MilestoneEvidence]
    transfer_mode: TransferMode | None = None
    stripe_transfer_id: str | None = None
    submitted_at: str | None = None
    released_at: str | None = None


class PlanSummary(BaseModel):
    id: str
    match_id: str
    request_id: str
    client_id: str
    provider_user_id: str
    provider_profile_id: str
    currency: str
    total_amount: float
    released_amount: float
    status: PlanStatus
    milestones: list[MilestoneSummary]
    created_at: str


class MilestoneStatusResponse(BaseModel):
    module: str
    status: str


class PlanResponse(BaseModel):
    module: str
    plan: PlanSummary


class PlanListResponse(BaseModel):
    module: str
    total: int
    items: list[PlanSummary]

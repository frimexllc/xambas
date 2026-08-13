from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    request_id: str
    provider_profile_id: str
    client_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewSummary(BaseModel):
    id: str
    request_id: str
    provider_profile_id: str
    client_id: str
    rating: int
    comment: str | None = None
    created_at: str


class ProviderReputationResponse(BaseModel):
    module: str
    provider_profile_id: str
    rating_avg: float
    jobs_completed: int
    reviews: list[ReviewSummary]


class ReviewListResponse(BaseModel):
    module: str
    total: int
    items: list[ReviewSummary]


class ReputationStatusResponse(BaseModel):
    module: str
    status: str
    collections: list[str]

from pydantic import BaseModel, Field


class PriceEstimate(BaseModel):
    min: float = Field(ge=0)
    max: float = Field(ge=0)
    currency: str = "MXN"


class GroqEstimate(BaseModel):
    """Forma exacta que exigimos al modelo de visión (validada con Pydantic)."""

    scope: list[str] = Field(min_length=1)
    estimated_price: PriceEstimate
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    suggested_title: str = Field(min_length=4, max_length=140)
    suggested_description: str = Field(min_length=10, max_length=2000)


class QuoteImage(BaseModel):
    path: str
    url: str
    content_type: str
    original_filename: str | None = None


class QuoteSummary(BaseModel):
    id: str
    client_id: str
    category_id: str | None = None
    category_name: str | None = None
    notes: str | None = None
    images: list[QuoteImage]
    scope: list[str]
    price_min: float
    price_max: float
    currency: str
    assumptions: list[str]
    confidence: float
    suggested_title: str
    suggested_description: str
    created_at: str


class AiQuoteStatusResponse(BaseModel):
    module: str
    status: str
    model: str
    provider: str


class QuoteResponse(BaseModel):
    module: str
    quote: QuoteSummary


class QuoteListResponse(BaseModel):
    module: str
    total: int
    items: list[QuoteSummary]

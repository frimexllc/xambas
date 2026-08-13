from pydantic import BaseModel, Field


class BrandSettings(BaseModel):
    brand_name: str = Field(default="Xambas", max_length=80)
    tagline: str = Field(
        default="Encuentra profesionales de confianza para tu hogar", max_length=200
    )
    logo_url: str | None = None
    primary_color: str = Field(default="#1f6feb", max_length=20)
    secondary_color: str = Field(default="#16794f", max_length=20)


class HowItWorksStep(BaseModel):
    title: str = Field(max_length=100)
    description: str = Field(max_length=300)


class LandingContent(BaseModel):
    hero_title: str = Field(
        default="Encuentra al profesional correcto en minutos", max_length=160
    )
    hero_subtitle: str = Field(
        default="Publica lo que necesitas y recibe propuestas de proveedores verificados.",
        max_length=300,
    )
    hero_image_url: str | None = None
    how_it_works: list[HowItWorksStep] = Field(default_factory=list)
    featured_category_ids: list[str] = Field(default_factory=list)


class SiteContentResponse(BaseModel):
    module: str
    brand: BrandSettings
    landing: LandingContent
    updated_at: str | None = None


class SiteContentUpdateRequest(BaseModel):
    brand: BrandSettings
    landing: LandingContent


class BusinessSettings(BaseModel):
    commission_rate_pct: float = Field(default=12.0, ge=0, le=100)
    payments_enabled: dict[str, list[str]] = Field(
        default_factory=lambda: {"MX": ["stripe", "mercado_pago"]}
    )
    matching_max_results: int = Field(default=10, ge=1, le=50)
    matching_min_score: int = Field(default=1, ge=0, le=100)


class BusinessSettingsResponse(BaseModel):
    module: str
    business: BusinessSettings
    updated_at: str | None = None


class BusinessSettingsUpdateRequest(BaseModel):
    business: BusinessSettings

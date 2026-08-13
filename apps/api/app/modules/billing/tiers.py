"""Modelo de comision escalonada.

Basado en la seccion 9 del estudio de investigacion de mercado:
comision del proveedor decreciente por nivel (10% -> 6%) + tarifa de
servicio al cliente del 5% (minimo $3, techo $250). Cifras marcadas
[SUPUESTO] en el estudio original: deben calibrarse con pruebas de
mercado antes de fijarse en produccion.
"""

from app.modules.billing.schemas import ProviderTierInfo, ProviderTierName

CLIENT_FEE_PCT = 5.0
CLIENT_FEE_MIN = 3.0
CLIENT_FEE_CAP = 250.0

# Orden: del nivel mas alto al mas bajo. El primero que cumpla todos los
# requisitos (jobs, rating, cancelacion) es el nivel asignado.
_TIER_RULES: list[tuple[ProviderTierName, int, float, float, float, str]] = [
    ("platino", 150, 4.8, 2.0, 6.0, "150+ trabajos, calificacion >=4.8, cancelacion <2%, sin disputas graves"),
    ("oro", 51, 4.7, 3.0, 7.5, "51-150 trabajos, calificacion >=4.7, cancelacion <3%"),
    ("plata", 11, 4.5, 5.0, 9.0, "11-50 trabajos, calificacion >=4.5, cancelacion <5%"),
    ("nuevo", 0, 0.0, 100.0, 10.0, "0-10 trabajos completados"),
]


def list_tiers() -> list[ProviderTierInfo]:
    # Se listan del nivel base al mas alto para que se vea como progresion.
    return [
        ProviderTierInfo(tier=name, commission_rate_pct=commission, requirements=requirements)
        for name, _, _, _, commission, requirements in reversed(_TIER_RULES)
    ]


def compute_provider_tier(
    jobs_completed: int, rating_avg: float, cancellation_rate_pct: float
) -> tuple[ProviderTierName, float]:
    for name, min_jobs, min_rating, max_cancel, commission, _ in _TIER_RULES:
        if jobs_completed >= min_jobs and rating_avg >= min_rating and cancellation_rate_pct <= max_cancel:
            return name, commission
    return "nuevo", 10.0


def compute_commission_quote(
    *, job_amount: float, jobs_completed: int, rating_avg: float, cancellation_rate_pct: float
) -> dict:
    tier, commission_pct = compute_provider_tier(jobs_completed, rating_avg, cancellation_rate_pct)

    provider_commission_amount = round(job_amount * commission_pct / 100, 2)
    client_fee_amount = round(job_amount * CLIENT_FEE_PCT / 100, 2)
    client_fee_amount = max(client_fee_amount, CLIENT_FEE_MIN)
    client_fee_amount = min(client_fee_amount, CLIENT_FEE_CAP)

    return {
        "provider_tier": tier,
        "provider_commission_pct": commission_pct,
        "provider_commission_amount": provider_commission_amount,
        "client_fee_amount": client_fee_amount,
        "client_total": round(job_amount + client_fee_amount, 2),
        "provider_receives": round(job_amount - provider_commission_amount, 2),
        "platform_revenue": round(provider_commission_amount + client_fee_amount, 2),
    }

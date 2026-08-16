from fastapi import HTTPException, status

from app.modules.billing import tiers
from app.modules.billing.payments_repository import PaymentsRepository
from app.modules.identity.repository import IdentityRepository
from app.modules.matching.repository import MatchingRepository
from app.modules.provider_dashboard.schemas import (
    DashboardMetrics,
    ProviderDashboardResponse,
    RecurringVisit,
)
from app.modules.recurring.repository import RecurringRepository


class ProviderDashboardService:
    def __init__(self) -> None:
        self._matching = MatchingRepository()
        self._identity = IdentityRepository()
        self._payments = PaymentsRepository()
        self._recurring = RecurringRepository()

    async def get_dashboard(
        self, *, provider_user_id: str, provider_profile_id: str
    ) -> ProviderDashboardResponse:
        profile = await self._identity.get_provider_profile_by_id(provider_profile_id)
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "provider_profile no encontrado")

        tier, commission_pct = tiers.compute_provider_tier(
            profile.get("jobs_completed", 0),
            profile.get("rating_avg", 0.0),
            profile.get("cancellation_rate", 0.0),
        )

        matches = await self._matching.list_matches_for_provider(provider_user_id)
        active_opportunities = sum(1 for m in matches if m["status"] == "suggested")
        accepted_jobs = sum(1 for m in matches if m["status"] == "accepted")

        payments = await self._payments.list_for_provider(provider_user_id)
        earnings_released = round(
            sum(p.get("provider_receives", 0.0) for p in payments if p["status"] == "released"), 2
        )
        earnings_in_escrow = round(
            sum(p.get("provider_receives", 0.0) for p in payments if p["status"] == "held_in_escrow"),
            2,
        )

        metrics = DashboardMetrics(
            tier=tier,
            commission_pct=commission_pct,
            rating_avg=round(profile.get("rating_avg", 0.0), 2),
            jobs_completed=profile.get("jobs_completed", 0),
            active_opportunities=active_opportunities,
            accepted_jobs=accepted_jobs,
            earnings_released=earnings_released,
            earnings_in_escrow=earnings_in_escrow,
        )

        # Visitas recurrentes asignadas: ocurrencias cuyas solicitudes hicieron match con este proveedor
        match_by_request = {m["request_id"]: m for m in matches}
        occurrences = await self._recurring.list_occurrences_for_requests(list(match_by_request.keys()))
        subscription_ids = list({o["subscription_id"] for o in occurrences})
        subscriptions = await self._recurring.get_subscriptions_by_ids(subscription_ids)

        recurring_visits = []
        for occurrence in occurrences:
            match = match_by_request.get(occurrence["request_id"])
            subscription = subscriptions.get(occurrence["subscription_id"], {})
            if match is None:
                continue
            recurring_visits.append(
                RecurringVisit(
                    subscription_id=occurrence["subscription_id"],
                    title=subscription.get("title", "Servicio recurrente"),
                    frequency=subscription.get("frequency", ""),
                    scheduled_date=occurrence["scheduled_date"],
                    request_id=occurrence["request_id"],
                    match_id=match["_id"].__str__() if "_id" in match else match.get("id", ""),
                    match_status=match["status"],
                )
            )

        return ProviderDashboardResponse(
            module="provider_dashboard",
            provider_user_id=provider_user_id,
            metrics=metrics,
            recurring_visits=recurring_visits,
        )


provider_dashboard_service = ProviderDashboardService()

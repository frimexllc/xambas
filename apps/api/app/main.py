from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.admin.management_router import router as admin_management_router
from app.modules.admin.router import router as admin_router
from app.modules.admin.service import admin_service
from app.modules.ai_quote.router import router as ai_quote_router
from app.modules.ai_quote.service import ai_quote_service
from app.modules.billing.router import router as billing_router
from app.modules.billing.payments_service import payments_service
from app.modules.content.router import router as content_router
from app.modules.identity.router import router as identity_router
from app.modules.identity.service import identity_service
from app.modules.matching.router import router as matching_router
from app.modules.matching.service import matching_service
from app.modules.messaging.router import router as messaging_router
from app.modules.messaging.service import messaging_service
from app.modules.milestones.router import router as milestones_router
from app.modules.milestones.service import milestones_service
from app.modules.provider_dashboard.router import router as provider_dashboard_router
from app.modules.recurring.router import router as recurring_router
from app.modules.recurring.service import recurring_service
from app.modules.reputation.router import router as reputation_router
from app.modules.reputation.service import reputation_service

app = FastAPI(title=settings.app_name)

allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")
api_router.include_router(identity_router)
api_router.include_router(matching_router)
api_router.include_router(billing_router)
api_router.include_router(messaging_router)
api_router.include_router(recurring_router)
api_router.include_router(ai_quote_router)
api_router.include_router(milestones_router)
api_router.include_router(provider_dashboard_router)
api_router.include_router(reputation_router)
api_router.include_router(admin_router)
api_router.include_router(admin_management_router)
api_router.include_router(content_router)


@app.on_event("startup")
async def on_startup() -> None:
    await identity_service.ensure_indexes()
    await matching_service.ensure_indexes()
    await matching_service.ensure_launch_categories()
    await messaging_service.ensure_indexes()
    await recurring_service.ensure_indexes()
    await ai_quote_service.ensure_indexes()
    await reputation_service.ensure_indexes()
    await admin_service.ensure_indexes()
    await payments_service.ensure_indexes()
    try:
        ai_quote_service.init_storage()
    except Exception:  # noqa: BLE001 - el storage no debe tumbar el arranque
        pass


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


app.include_router(api_router)

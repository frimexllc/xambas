from fastapi import APIRouter, FastAPI

from app.core.config import settings
from app.modules.billing.router import router as billing_router
from app.modules.identity.router import router as identity_router
from app.modules.identity.service import identity_service
from app.modules.matching.router import router as matching_router
from app.modules.matching.service import matching_service
from app.modules.messaging.router import router as messaging_router
from app.modules.reputation.router import router as reputation_router

app = FastAPI(title=settings.app_name)

api_router = APIRouter(prefix="/api")
api_router.include_router(identity_router)
api_router.include_router(matching_router)
api_router.include_router(billing_router)
api_router.include_router(messaging_router)
api_router.include_router(reputation_router)


@app.on_event("startup")
async def on_startup() -> None:
    await identity_service.ensure_indexes()
    await matching_service.ensure_indexes()
    await matching_service.ensure_launch_categories()


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


app.include_router(api_router)

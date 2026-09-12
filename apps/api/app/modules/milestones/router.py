from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.modules.identity.dependencies import get_current_user, require_client, require_provider
from app.modules.identity.schemas import UserSummary
from app.modules.milestones.schemas import (
    MilestoneStatusResponse,
    PlanCreateRequest,
    PlanListResponse,
    PlanResponse,
)
from app.modules.milestones.service import milestones_service

router = APIRouter(prefix="/milestones", tags=["milestones"])


@router.get("/status")
def milestones_status() -> MilestoneStatusResponse:
    return milestones_service.get_status()


@router.post("/plans")
async def create_plan(
    payload: PlanCreateRequest,
    current_user: UserSummary = Depends(require_client),
) -> PlanResponse:
    payload = payload.model_copy(update={"client_id": current_user.id})
    return await milestones_service.create_plan(payload)


@router.get("/plans")
async def list_plans(
    current_user: UserSummary = Depends(get_current_user),
) -> PlanListResponse:
    # "Mis planes": como cliente o como proveedor, según el rol de la cuenta.
    if current_user.role == "provider":
        return await milestones_service.list_plans(client_id=None, provider_user_id=current_user.id)
    return await milestones_service.list_plans(client_id=current_user.id, provider_user_id=None)


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> PlanResponse:
    return await milestones_service.get_plan(plan_id, acting_user_id=current_user.id)


@router.post("/plans/{plan_id}/milestones/{milestone_id}/submit")
async def submit_evidence(
    plan_id: str,
    milestone_id: str,
    files: list[UploadFile] = File(...),
    current_user: UserSummary = Depends(require_provider),
) -> PlanResponse:
    return await milestones_service.submit_evidence(
        plan_id, milestone_id, provider_user_id=current_user.id, files=files
    )


@router.post("/plans/{plan_id}/milestones/{milestone_id}/release")
async def approve_release(
    plan_id: str,
    milestone_id: str,
    current_user: UserSummary = Depends(require_client),
) -> PlanResponse:
    return await milestones_service.approve_and_release(
        plan_id, milestone_id, client_id=current_user.id
    )


# Sin auth por header a propósito (URL-capacidad con UUID irrepetible): las
# etiquetas <img> del navegador no envían Authorization.
@router.get("/files/{path:path}")
async def get_file(path: str) -> Response:
    content, content_type = await milestones_service.get_file(path)
    return Response(content=content, media_type=content_type)

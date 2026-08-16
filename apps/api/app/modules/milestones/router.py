from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import Response

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
async def create_plan(payload: PlanCreateRequest) -> PlanResponse:
    return await milestones_service.create_plan(payload)


@router.get("/plans")
async def list_plans(
    client_id: str | None = Query(default=None),
    provider_user_id: str | None = Query(default=None),
) -> PlanListResponse:
    return await milestones_service.list_plans(
        client_id=client_id, provider_user_id=provider_user_id
    )


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str) -> PlanResponse:
    return await milestones_service.get_plan(plan_id)


@router.post("/plans/{plan_id}/milestones/{milestone_id}/submit")
async def submit_evidence(
    plan_id: str,
    milestone_id: str,
    provider_user_id: str = Query(...),
    files: list[UploadFile] = File(...),
) -> PlanResponse:
    return await milestones_service.submit_evidence(
        plan_id, milestone_id, provider_user_id=provider_user_id, files=files
    )


@router.post("/plans/{plan_id}/milestones/{milestone_id}/release")
async def approve_release(
    plan_id: str, milestone_id: str, client_id: str = Query(...)
) -> PlanResponse:
    return await milestones_service.approve_and_release(plan_id, milestone_id, client_id=client_id)


@router.get("/files/{path:path}")
async def get_file(path: str) -> Response:
    content, content_type = await milestones_service.get_file(path)
    return Response(content=content, media_type=content_type)

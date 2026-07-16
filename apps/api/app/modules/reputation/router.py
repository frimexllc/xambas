from fastapi import APIRouter

router = APIRouter(prefix="/reputation", tags=["reputation"])


@router.get("/status")
def reputation_status() -> dict[str, str]:
    return {"module": "reputation", "status": "ready"}

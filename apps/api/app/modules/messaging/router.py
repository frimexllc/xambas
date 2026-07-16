from fastapi import APIRouter

router = APIRouter(prefix="/messaging", tags=["messaging"])


@router.get("/status")
def messaging_status() -> dict[str, str]:
    return {"module": "messaging", "status": "ready"}

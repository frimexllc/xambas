from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.modules.ai_quote.schemas import (
    AiQuoteStatusResponse,
    QuoteListResponse,
    QuoteResponse,
)
from app.modules.ai_quote.service import ai_quote_service
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.schemas import UserSummary

router = APIRouter(prefix="/ai-quote", tags=["ai_quote"])


@router.get("/status")
def ai_quote_status() -> AiQuoteStatusResponse:
    return ai_quote_service.get_status()


@router.post("/estimate")
async def create_estimate(
    category_id: str | None = Form(None),
    notes: str | None = Form(None),
    files: list[UploadFile] = File(...),
    current_user: UserSummary = Depends(get_current_user),
) -> QuoteResponse:
    # El cliente sale del token; ya no se acepta client_id por el formulario.
    return await ai_quote_service.create_estimate(
        client_id=current_user.id,
        category_id=category_id,
        notes=notes,
        files=files,
    )


@router.get("/estimates")
async def list_estimates(
    current_user: UserSummary = Depends(get_current_user),
) -> QuoteListResponse:
    return await ai_quote_service.list_estimates(client_id=current_user.id)


@router.get("/estimates/{quote_id}")
async def get_estimate(
    quote_id: str,
    current_user: UserSummary = Depends(get_current_user),
) -> QuoteResponse:
    return await ai_quote_service.get_estimate(quote_id, acting_user_id=current_user.id)


# Sin auth por header a propósito: las etiquetas <img> del navegador no mandan
# Authorization. La protección es la URL-capacidad (ruta con client_id + UUID
# aleatorio irrepetible). Mismo criterio que /api/milestones/files/*.
@router.get("/files/{path:path}")
async def get_file(path: str) -> Response:
    content, content_type = await ai_quote_service.get_file(path)
    return Response(content=content, media_type=content_type)

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import Response

from app.modules.ai_quote.schemas import (
    AiQuoteStatusResponse,
    QuoteListResponse,
    QuoteResponse,
)
from app.modules.ai_quote.service import ai_quote_service

router = APIRouter(prefix="/ai-quote", tags=["ai_quote"])


@router.get("/status")
def ai_quote_status() -> AiQuoteStatusResponse:
    return ai_quote_service.get_status()


@router.post("/estimate")
async def create_estimate(
    client_id: str = Form(...),
    category_id: str | None = Form(None),
    notes: str | None = Form(None),
    files: list[UploadFile] = File(...),
) -> QuoteResponse:
    return await ai_quote_service.create_estimate(
        client_id=client_id,
        category_id=category_id,
        notes=notes,
        files=files,
    )


@router.get("/estimates")
async def list_estimates(client_id: str | None = Query(default=None)) -> QuoteListResponse:
    return await ai_quote_service.list_estimates(client_id=client_id)


@router.get("/estimates/{quote_id}")
async def get_estimate(quote_id: str) -> QuoteResponse:
    return await ai_quote_service.get_estimate(quote_id)


@router.get("/files/{path:path}")
async def get_file(path: str) -> Response:
    content, content_type = await ai_quote_service.get_file(path)
    return Response(content=content, media_type=content_type)

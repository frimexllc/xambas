import asyncio
import base64
import json
import uuid

from bson.errors import InvalidId
from fastapi import HTTPException, UploadFile, status
from groq import AsyncGroq
from pydantic import ValidationError

from app.core.config import settings
from app.core.storage import object_storage
from app.modules.ai_quote.repository import AiQuoteRepository
from app.modules.ai_quote.schemas import (
    AiQuoteStatusResponse,
    GroqEstimate,
    QuoteImage,
    QuoteListResponse,
    QuoteResponse,
    QuoteSummary,
)
from app.modules.identity.repository import IdentityRepository
from app.modules.matching.service import matching_service

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 10 * 1024 * 1024
_MAX_IMAGES = 5
_EXT_BY_TYPE = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

_SYSTEM_PROMPT = """Eres un estimador experto de servicios del hogar en México.
A partir de una o varias FOTOS del trabajo (y contexto opcional), devuelves ÚNICAMENTE
un JSON válido con EXACTAMENTE esta forma:
{
  "scope": ["tarea concreta visible en la foto"],
  "estimated_price": {"min": 0, "max": 0, "currency": "MXN"},
  "assumptions": ["supuesto o dato faltante relevante"],
  "confidence": 0.0,
  "suggested_title": "título breve para publicar la solicitud",
  "suggested_description": "descripción clara del trabajo para el proveedor"
}
Reglas:
- Precios numéricos en pesos mexicanos (MXN), sin símbolos, min <= max.
- No afirmes certeza absoluta desde una imagen: menciona en 'assumptions' lo que falta
  (medidas, materiales, acceso, alcance real, daños ocultos).
- Si la foto no es clara o no corresponde a un servicio, usa confianza baja y explícalo.
- Responde en español. No agregues texto fuera del JSON."""


class AiQuoteService:
    def __init__(self) -> None:
        self._repository = AiQuoteRepository()
        self._identity_repository = IdentityRepository()
        self._groq: AsyncGroq | None = None

    async def ensure_indexes(self) -> None:
        await self._repository.ensure_indexes()

    def init_storage(self) -> None:
        object_storage.init()

    def get_status(self) -> AiQuoteStatusResponse:
        return AiQuoteStatusResponse(
            module="ai_quote",
            status="ready" if settings.groq_api_key else "missing_api_key",
            model=settings.groq_vision_model,
            provider="groq",
        )

    def _client(self) -> AsyncGroq:
        if not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GROQ_API_KEY no configurada",
            )
        if self._groq is None:
            self._groq = AsyncGroq(api_key=settings.groq_api_key)
        return self._groq

    async def create_estimate(
        self,
        *,
        client_id: str,
        category_id: str | None,
        notes: str | None,
        files: list[UploadFile],
    ) -> QuoteResponse:
        await self._get_user_document_or_404(client_id)

        if not files:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "sube al menos una foto")
        if len(files) > _MAX_IMAGES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"máximo {_MAX_IMAGES} fotos")

        category_name: str | None = None
        if category_id:
            category = await matching_service.get_category(category_id)
            category_name = category.name

        images: list[QuoteImage] = []
        data_urls: list[str] = []
        for upload in files:
            if upload.content_type not in _ALLOWED_TYPES:
                raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "usa JPEG, PNG o WebP")
            content = await upload.read()
            if not content:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "archivo vacío")
            if len(content) > _MAX_BYTES:
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "cada foto máx 10 MB")

            ext = _EXT_BY_TYPE[upload.content_type]
            path = f"{settings.storage_app_name}/ai-quote/{client_id}/{uuid.uuid4().hex}.{ext}"
            stored = await asyncio.to_thread(
                object_storage.put_object, path, content, upload.content_type
            )
            stored_path = stored["path"]
            images.append(
                QuoteImage(
                    path=stored_path,
                    url=f"/api/ai-quote/files/{stored_path}",
                    content_type=upload.content_type,
                    original_filename=upload.filename,
                )
            )
            encoded = base64.b64encode(content).decode("utf-8")
            data_urls.append(f"data:{upload.content_type};base64,{encoded}")

        estimate = await self._run_vision(category_name=category_name, notes=notes, data_urls=data_urls)

        document = {
            "client_id": client_id,
            "category_id": category_id,
            "category_name": category_name,
            "notes": notes,
            "images": [image.model_dump() for image in images],
            "scope": estimate.scope,
            "price_min": estimate.estimated_price.min,
            "price_max": estimate.estimated_price.max,
            "currency": estimate.estimated_price.currency,
            "assumptions": estimate.assumptions,
            "confidence": estimate.confidence,
            "suggested_title": estimate.suggested_title,
            "suggested_description": estimate.suggested_description,
        }
        document = await self._repository.create_quote(document)
        return QuoteResponse(module="ai_quote", quote=self._serialize_quote(document))

    async def _run_vision(
        self,
        *,
        category_name: str | None,
        notes: str | None,
        data_urls: list[str],
    ) -> GroqEstimate:
        context_lines = []
        if category_name:
            context_lines.append(f"Categoría de servicio: {category_name}.")
        if notes:
            context_lines.append(f"Notas del cliente: {notes}")
        context = " ".join(context_lines) or "Sin contexto adicional."

        user_content: list[dict] = [
            {"type": "text", "text": f"{context}\nAnaliza las fotos y entrega el JSON pedido."}
        ]
        for url in data_urls:
            user_content.append({"type": "image_url", "image_url": {"url": url}})

        try:
            completion = await self._client().chat.completions.create(
                model=settings.groq_vision_model,
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger("ai_quote").exception("Groq vision call failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="el análisis con IA falló, intenta de nuevo",
            ) from exc

        raw = completion.choices[0].message.content or ""
        try:
            return GroqEstimate.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="la IA devolvió un resultado no válido, intenta de nuevo",
            ) from exc

    async def list_estimates(self, client_id: str | None = None) -> QuoteListResponse:
        if client_id is not None:
            await self._get_user_document_or_404(client_id)
        documents = await self._repository.list_quotes(client_id=client_id)
        return QuoteListResponse(
            module="ai_quote",
            total=len(documents),
            items=[self._serialize_quote(document) for document in documents],
        )

    async def get_estimate(self, quote_id: str) -> QuoteResponse:
        try:
            document = await self._repository.get_quote_by_id(quote_id)
        except InvalidId as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "quote_id inválido") from exc
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "cotización no encontrada")
        return QuoteResponse(module="ai_quote", quote=self._serialize_quote(document))

    async def get_file(self, path: str) -> tuple[bytes, str]:
        prefix = f"{settings.storage_app_name}/ai-quote/"
        if not path.startswith(prefix):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "imagen no encontrada")
        try:
            return await asyncio.to_thread(object_storage.get_object, path)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_404_NOT_FOUND, "imagen no encontrada") from exc

    async def _get_user_document_or_404(self, user_id: str) -> dict:
        try:
            document = await self._identity_repository.get_user_by_id(user_id)
        except InvalidId as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "user_id inválido") from exc
        if document is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user no encontrado")
        return document

    def _serialize_quote(self, document: dict) -> QuoteSummary:
        return QuoteSummary(
            id=str(document["_id"]),
            client_id=document["client_id"],
            category_id=document.get("category_id"),
            category_name=document.get("category_name"),
            notes=document.get("notes"),
            images=[QuoteImage(**image) for image in document.get("images", [])],
            scope=document["scope"],
            price_min=document["price_min"],
            price_max=document["price_max"],
            currency=document["currency"],
            assumptions=document.get("assumptions", []),
            confidence=document["confidence"],
            suggested_title=document["suggested_title"],
            suggested_description=document["suggested_description"],
            created_at=str(document["_id"].generation_time.isoformat()),
        )


ai_quote_service = AiQuoteService()

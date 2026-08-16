# Xambas — Marketplace de Servicios del Hogar (PRD vivo)

## Problema / Visión
Marketplace que conecta clientes con proveedores de servicios del hogar. Diferenciador central (del estudio de mercado `docs/Marketplace_Servicios_Investigacion_y_Diseno.docx`): **comisión sobre transacción confirmada, no pago-por-lead**, pago en custodia (escrow), verificación creíble, anti-fuga por incentivos y herramientas reales de negocio para el proveedor.

## Arquitectura (monorepo "xambas", Yarn 4 workspaces)
- `apps/api` — FastAPI modular. Módulos: identity, matching, billing (Stripe Connect + Mercado Pago), messaging (anti-fuga), reputation, admin, content, **recurring (NUEVO)**.
- `apps/web` — landing pública (Vite).
- `apps/client` — app de cliente (Vite). **Es la app visible en el preview.**
- `apps/provider` — app de proveedor (Vite).
- `apps/admin` — panel admin (Vite).
- Persistencia: MongoDB (motor). Envelopes de respuesta con campo `module`; IDs de Mongo serializados como string.

## Adaptación al entorno de preview (Emergent)
El supervisor (config read-only) corre `uvicorn server:app` en `/app/backend:8001` y `yarn start` en `/app/frontend:3000`. Se crearon **shims** que puentean al monorepo sin moverlo:
- `/app/backend/server.py` → añade `/app/apps/api` al path e importa `app.main:app`. Config vía `/app/backend/.env` (MONGO_URI=mongodb://localhost:27017, DB=xambas_dev, OTP_PROVIDER=dev).
- `/app/frontend/start.sh` → corre Vite de `apps/${PREVIEW_APP:-client}` en `0.0.0.0:3000`. Para mostrar otra app (web/provider/admin): cambiar `PREVIEW_APP` o el default.
- `apps/client/.env` → `VITE_API_BASE_URL=/api` (mismo origen vía ingress).
- IMPORTANTE: uvicorn `--reload` solo observa `/app/backend`. Tras editar `/app/apps/api` hay que `sudo supervisorctl restart backend`.

## Implementado en esta sesión (Jun 2026)
- ✅ Stack completo corriendo en el preview (API + Mongo + app cliente), 19 categorías sembradas.
- ✅ **Servicios recurrentes / suscripciones** (feature #1 del backlog): módulo `recurring` + UI cliente. Testing: backend 13/13, frontend OK.
- ✅ **Cotización con IA** (feature: fotos → alcance + rango de precio antes de contactar):
  - Módulo `ai_quote`: subida de fotos, visión con **Groq** (modelo `qwen/qwen3.6-27b`; nota: `llama-4` NO estaba disponible en la cuenta), salida JSON validada con Pydantic, persistencia y servidor de imágenes con guardia de prefijo. Además permite **publicar una service_request** prellenada desde la estimación.
  - Almacenamiento: **Emergent Object Storage** (sin llaves; el usuario dio la key de Groq pero omitió R2). Capa `core/storage.py` con interfaz mínima para migrar a **Cloudflare R2 (boto3)** después sin tocar el resto.
  - UI cliente: 3ª pestaña "Cotización IA" (subir fotos, ver estimación, publicar). Testing: backend 10/10, frontend OK.
  - Llaves usadas: `GROQ_API_KEY` (usuario), `EMERGENT_LLM_KEY` (storage). `max_tokens=4096` para evitar json_validate_failed.

## Decisiones / pendientes de integración
- R2 pendiente: el usuario no dio credenciales; cuando las dé, reimplementar `core/storage.py` con boto3 (S3-compatible) y variables R2_*.
- Modelo de visión: cambiar a Llama 4 si la cuenta de Groq obtiene acceso (config `GROQ_VISION_MODEL`).

## Implementado en esta sesión (histórico previo)

## Estado previo ya existente (verificado en repo)
Registro+OTP, categorías/subcategorías, service_requests con matching automático, chat anti-fuga, reviews/reputación, pagos en custodia con Stripe Connect (requiere claves), panel admin y contenido de landing.

## Backlog priorizado (elegido por el usuario, orden confirmado)
1. ✅ Cotización con IA (hecho).
2. ⏭️ **Pagos por etapas (milestones)** para proyectos grandes (extiende `billing`; Stripe test key `sk_test_emergent` ya en el entorno).
3. **Panel de negocio del proveedor** (calendario, ingresos, métricas) — app `provider`.
4. **Recurrentes en Provider** (ver/confirmar visitas recurrentes asignadas) — app `provider`.
5. **Llaves reales**: Twilio (OTP SMS) — el usuario lo activará más tarde; R2 pendiente.

## Deuda técnica / mejoras (no bloqueantes)
- Auth por token en endpoints `/api/recurring/*` y `/api/ai-quote/*` (hoy solo por client_id, Fase 0).
- Refactor: dividir `apps/client/src/App.jsx` (>1500 líneas) en archivos por pestaña (RequestsPanel, RecurringPanel, AiQuotePanel).
- `ai_quote`: down-scale de imágenes (PIL) antes de enviar a Groq para grandes cargas.
- Preview: exponer también web/provider/admin (hoy solo cliente; se alterna con `PREVIEW_APP`).

## Notas de negocio (posicionamiento vs competencia)
Comisión escalonada por nivel ya modelada (`billing/tiers.py`). Servicios recurrentes refuerzan retención/lealtad (menor incentivo de fuga), alineado con la tesis del estudio.

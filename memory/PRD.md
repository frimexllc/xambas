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
- ✅ **Servicios recurrentes / suscripciones** (feature #1 del backlog del usuario):
  - Backend `recurring`: crear suscripción (frecuencia weekly/biweekly/monthly), generar visitas (crea `service_request` real vía matching y registra `occurrence`, avanza `next_run_date`), pausar/reanudar/cancelar (máquina de estados con 409 correctos), listar por cliente y listar visitas.
  - Frontend cliente: pestañas Solicitudes / Servicios recurrentes; formulario de nueva suscripción; lista con acciones (generar visita, pausar/reanudar/cancelar, ver visitas). data-testids en todos los interactivos.
  - Validado por testing agent: backend 13/13, frontend happy path + regresión. Sin bugs.

## Estado previo ya existente (verificado en repo)
Registro+OTP, categorías/subcategorías, service_requests con matching automático, chat anti-fuga, reviews/reputación, pagos en custodia con Stripe Connect (requiere claves), panel admin y contenido de landing.

## Backlog priorizado (elegido por el usuario)
- P0 (siguiente): **Cotización asistida por IA a partir de fotos** (Fase 2 del estudio).
- P1: **Pagos por etapas (milestones)** para proyectos grandes.
- P1: **Panel de negocio del proveedor** (CRM ligero, facturación, métricas).
- P2 / mejoras: exponer también web/provider/admin en preview; auth real por token en endpoints; refactor de `apps/client/src/App.jsx` (dividir componentes recurring en archivos propios); `next_run_date = max(next+delta, hoy)` si una suscripción estuvo pausada.

## Notas de negocio (posicionamiento vs competencia)
Comisión escalonada por nivel ya modelada (`billing/tiers.py`). Servicios recurrentes refuerzan retención/lealtad (menor incentivo de fuga), alineado con la tesis del estudio.

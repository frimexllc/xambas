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
El supervisor (config read-only) corre `uvicorn server:app` en `/app/backend:8000` y `yarn start` en `/app/frontend:3000`. Se crearon **shims** que puentean al monorepo sin moverlo:
- `/app/backend/server.py` → añade `/app/apps/api` al path e importa `app.main:app`. Config vía `/app/backend/.env` (MONGO_URI=mongodb://localhost:27017, DB=xambas_dev, OTP_PROVIDER=dev).
- `/app/frontend/start.sh` → corre Vite de `apps/${PREVIEW_APP:-client}` en `0.0.0.0:3000`. Para mostrar otra app (web/provider/admin): cambiar `PREVIEW_APP` o el default.
- `apps/client/.env` → `VITE_API_BASE_URL=/api` (mismo origen vía ingress).
- IMPORTANTE: uvicorn `--reload` solo observa `/app/backend`. Tras editar `/app/apps/api` hay que `sudo supervisorctl restart backend`.

## Implementado en esta sesión (Sep 2026) — CI e infraestructura de pruebas
- ✅ **GitHub Actions** (`.github/workflows/ci.yml`): job `backend` (Mongo + API + `pytest`) y job `frontend` (`yarn install` + build de las 4 apps) en cada push a `main`/`develop` y en cada PR.
- ✅ **Suite de integración migrada** de `backend/tests/` (entorno Emergent) a `apps/api/tests/`:
  - `conftest.py` + `helpers.py` compartidos. La URL base se resuelve por env (`XAMBAS_API_URL` → `REACT_APP_BACKEND_URL` → `localhost:8000`).
  - IDs de categoría **resueltos en runtime** contra el catálogo sembrado (antes hardcodeados; se rompían con una BD limpia).
  - Imágenes de prueba generadas en memoria con Pillow (antes rutas fijas `/app/*.jpg`, `/tmp/*.jpg`).
  - Marcador `external` para las pruebas que llaman a Groq de verdad; se saltan salvo `XAMBAS_RUN_EXTERNAL_TESTS=1`.
  - `pytest` + `pillow` en `[dependency-groups] dev` de `apps/api/pyproject.toml`. Estado: 33 passed, 4 skipped (external) en local.
- ✅ **Backend de almacenamiento `local`** en `core/storage.py` (`STORAGE_PROVIDER=local`, opcional `STORAGE_LOCAL_DIR`): sistema de archivos, sin red ni credenciales de Emergent. Lo usa el CI y sirve para desarrollo local sin llaves.
- ✅ **Credenciales**: `memory/test_credentials.md` revisado — no contiene secretos reales (solo describe el flujo OTP dev). Se deja en el repo.
- ✅ **Tests de frontend** (Sep 2026): Vitest + Testing Library + jsdom en `apps/client`. 6 archivos / 19 casos: `lib/api.js` (el Bearer se adjunta/limpia con `setAuthToken`), `AuthFlow` (registro→OTP→token), `ClientHome` (ruteo de pestañas), `RequestsPanel`, `RecurringPanel`, `AiQuotePanel` (con `api` mockeado). Corre en el job `frontend` del CI (`yarn workspace client test`). Se añadió `.yarnrc.yml` con un `packageExtensions` para declarar el peer `vitest` que `@testing-library/jest-dom` no declara (PnP estricto lo rechazaba).
- ⚠️ **`.pnp.cjs`**: sigue desincronizándose (aparece como modificado casi siempre). Por eso el CI usa `yarn install` sin `--immutable`. Pendiente: regenerarlo limpio y commitearlo solo, o evaluar `nodeLinker: node-modules`.

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
- ✅ **Auth por token en `/api/recurring/*` y `/api/ai-quote/*`** (Sep 2026): dependencia `get_current_user` (header `Authorization: Bearer <token>`, mismo token que emite `otp/verify`) en `app/modules/identity/dependencies.py`. El `client_id` se toma del token, nunca del body; los endpoints por-id validan propiedad (403 si la suscripción/cotización es de otro cliente). `/status` y `/ai-quote/files/*` quedan públicos a propósito (este último es URL-capacidad, como `/milestones/files/*`, porque las `<img>` del navegador no mandan header). Frontend `apps/client`: `lib/api.js` adjunta el Bearer y rehidrata el token al cargar.
  - ✅ **Ampliado a `billing` + `milestones`** (Sep 2026): `require_client` / `require_provider` (nuevo) en `dependencies.py`. `POST /billing/payments`, `confirm-completion`, `GET /billing/payments[/{id}]`, `connect/onboarding-link`, `connect/status`; y todo `/milestones/plans*` + submit/release. Frontend `apps/provider` también adjunta el Bearer ahora.
  - ✅ **Ampliado a `matching` + `messaging` + `reputation` + `provider_dashboard`** (Sep 2026): `POST/GET /matching/service-requests[/{id}]`, `/run`, `/matches`, `/providers/{id}/matches`, `/matches/{id}/accept`; todo `/messaging/*` (el emisor y su rol salen del token+hilo, no del body; solo participantes leen/escriben); `POST /reputation/reviews` (valida que la solicitud sea del cliente); `GET /provider/dashboard`. Públicos a propósito: `/*/status`, `/matching/categories*`, `/billing/{status,tiers,provider,commission/quote}`, `GET /reputation/providers/{id}` (reputación es visible) y `GET /*/files/{path}`. Tests nuevos: `test_matching.py` (12), `test_messaging.py` (7). **Deuda de auth cerrada.** Total backend: 75 passed, 5 skipped.
- ✅ **Refactor de `apps/client/src/App.jsx`** (Sep 2026): de 1758 líneas a 65 (solo el shell). Extraído a `components/` (AuthFlow, ChatPanel, StatusBadge) y `panels/` (ClientHome orquesta las pestañas; RequestsPanel + RecurringPanel + AiQuotePanel + MilestonesPanel). `constants.js` para `COUNTRY_CODE`. Sin cambio de lógica; movimiento verbatim salvo dos detalles: (1) la barra de pestañas ahora queda visible en el detalle de solicitud (antes lo tapaba), (2) cada panel se re-monta al cambiar de pestaña, así que refresca sus datos. Verificado con `yarn build:client` (no hay tests de frontend todavía).
- ✅ **Login de cuenta existente** (Sep 2026): `POST /api/identity/login` con `{identifier}` (teléfono o correo) → busca al usuario → dispara OTP `purpose=login` → devuelve `user_id` + `challenge_id` + `debug_code`; se completa con `otp/verify` (que ya crea la sesión). Antes solo había `bootstrap` (409 si la cuenta existía), así que "iniciar sesión" era re-leer `localStorage`. Frontends `client` y `provider`: `AuthFlow` ahora tiene toggle registro↔login. Tests: `test_identity.py` (3) + caso de login en `AuthFlow.test.jsx`. `apps/client` frontend: 20 passed.
- ✅ **Rate limiting** (Sep 2026): `app/core/rate_limit.py` — ventana fija respaldada por Mongo (`find_one_and_update` atómico con clave `<key>:<bucket-de-tiempo>`, TTL para limpiar solo). Aplica a `POST /identity/otp/request` (por `user_id`) y `POST /identity/login` (por `identifier`); el límite adicional por IP solo corre con un proveedor de OTP real (`OTP_PROVIDER != dev`), porque en dev no hay envío real que proteger. Config en `Settings` (`otp_request_limit_per_user`, `login_limit_per_identifier`, `rate_limit_window_minutes`, etc.), todos con default. Tests: 3 nuevos en `test_identity.py` (no asumen el valor exacto del límite, repiten hasta ver 429). Backend: 81 passed.
- Deuda menor pendiente: validar Stripe contra la API real (necesita `stripe listen` con llaves del usuario); down-scale de imágenes antes de Groq.

## UX/UI (Sep 2026) — pulido conservador, solo `apps/client`
El usuario pidió invertir en UX/UI; eligió alcance "solo cliente primero" e intensidad "pulido conservador" (arreglar inconsistencias concretas, no traer todavía la identidad visual completa del landing — tickets/plano técnico — a las apps internas; esa opción sigue disponible si se quiere después).
- **Dropzone de fotos** (`components/PhotoDropzone.jsx`): sustituye el `<input type="file">` nativo en `AiQuotePanel` (rompía el estilo del resto del formulario). Arrastrar-y-soltar, miniaturas con botón de quitar, respeta `maxFiles`. El input real queda oculto con el mismo `data-testid` para no romper accesibilidad ni tests.
- **Estados vacíos** (`components/EmptyState.jsx`): ícono + título + pista de la acción, en vez de una línea de texto plano. Aplicado en Requests, Recurring, AiQuote y Milestones.
- **Micro-interacciones**: sombra sutil en `.card`, elevación al hover en `.request-item` y en `.btn-primary`, transiciones consistentes.
- Tests: `PhotoDropzone.test.jsx` (5, cubre input/drag-drop/maxFiles/quitar). Polyfill de `URL.createObjectURL` en `test/setup.js` (jsdom no lo trae). Frontend cliente: 25 passed.
- Pendiente si se quiere seguir: mismo pulido en `apps/provider`; luego, si se decide, la opción de "identidad visual completa" (tickets con folio, plano técnico) que se dejó de lado esta vez.

## Rediseño completo de `apps/client` (Sep 2026) — "Orden de trabajo, refinado"
El pulido conservador no convenció ("no me gusta, quiero algo más elegante"). Se armaron 3 direcciones visuales completas (mockups reales, no descripciones) en un canvas de diseño para elegir entre ellas; el usuario pidió avanzar directo a un rediseño completo sin genericidad. Se ejecutó una evolución de la dirección **A "Orden de trabajo, refinado"** (la más fiel a la marca real del landing y la más sostenible para una app de uso diario), con el sello de confianza de la dirección C usado con moderación en pagos.

Fuente real usada (no inventada): `apps/web/src/App.css` y `App.jsx` — paleta, tipografía y componentes (`.stub-number`, `.category-card`, `.btn-primary` con sombra dura, `.blueprint-frame` con grid) ya validados en el landing.

- **`App.css` reescrito por completo**: radios de 8-10px → 3-4px, bordes finos en vez de cajas grises, botón primario con la sombra dura `3px 3px 0 var(--primary-shadow)` (idéntica a la del landing), pestañas como ficha de orden (mono, subrayado de acento) en vez de píldora flotante, badges tipo estampa (mono, `--radius-sm`, sin forma de píldora) en vez de chips redondos, `.folio-header`/`.folio-card` (encabezado tipo ticket con folio) reutilizable, `.readout-panel` (panel técnico con grid sutil de fondo, para precios/estimaciones), `.mono-label`/`.field-label` para toda etiqueta de campo.
- **Set de íconos de trazo nuevo** (`components/icons.jsx`): Clipboard, Repeat, Camera, Receipt, Check, Seal, Lock — reemplaza todo el emoji de la interfaz de trabajo (📋🔁📸🧾✅🔒🔓📷). La marca sigue usando emoji en el landing para categorías (precedente existente); la app de trabajo usa trazo técnico consistente.
- Aplicado en **las 4 pestañas** + autenticación: folio header en las tarjetas de alta (nueva solicitud, nueva suscripción, cotización IA), panel técnico con grid para el rango de precio estimado, checklist con ícono de check para el alcance, sello de confianza al liberar un pago, códigos de folio mono en listas (solicitudes, planes por etapas).
- Verificado: `yarn build:client` OK, **25/25 tests pasan** sin cambios (la reescritura de estilos no tocó comportamiento), capturas de pantalla del formulario de registro/login confirmando el render.
- Pendiente si se quiere seguir: el mismo tratamiento en `apps/provider` (hoy solo tiene el pulido conservador del pase anterior); revisión visual del resto de subpantallas (chat, detalle de solicitud con matches) que heredan el sistema por CSS pero no se retocaron a mano una por una.
- `ai_quote`: down-scale de imágenes (PIL) antes de enviar a Groq para grandes cargas.
- Preview: exponer también web/provider/admin (hoy solo cliente; se alterna con `PREVIEW_APP`).

## Notas de negocio (posicionamiento vs competencia)
Comisión escalonada por nivel ya modelada (`billing/tiers.py`). Servicios recurrentes refuerzan retención/lealtad (menor incentivo de fuga), alineado con la tesis del estudio.

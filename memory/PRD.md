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

**⚠️ SUPERADO por el rediseño Apple HIG de abajo.** El sistema "Orden de trabajo, refinado" (ticket/folio, plano técnico, sombra dura) duró una sola sesión: el usuario lo probó y dijo "no me gusta, usa el HIG de Apple, eso se ve genérico". Se deja esta sección como registro de que ya se intentó y por qué no funcionó (evitar repetirlo).

## Rediseño de marca completa: Apple HIG (Sep 2026) — las 4 apps
Segundo rediseño de la sesión. El primero (arriba) no convenció; se probó también una dirección oscura tipo dashboard/fintech (acento índigo) y el usuario la rechazó por "genérica" — es el patrón de diseño más repetido en interfaces generadas por IA ahora mismo, así que la objeción era acertada. Se pidió explícitamente **usar las Human Interface Guidelines de Apple** y que el resultado no se sintiera genérico. Se validó con un mockup en un canvas de diseño antes de tocar las 4 apps (`https://claude.ai/code/artifact/2756ffe2-5f1c-4834-87c7-f20c5a45b484`), y el usuario dio luz verde ("continua sorpréndeme").

**Decisión de alcance** (confirmada explícitamente por el usuario): reemplaza la paleta en **las 4 apps** — `client`, `provider`, `admin` y el `web` (landing) — no solo las internas.

### Sistema
- **Tipografía del sistema, no un archivo de fuente**: `-apple-system, BlinkMacSystemFont, "SF Pro Text/Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif`. En Mac/iPhone esto renderiza San Francisco de verdad; en Windows cae a Segoe UI. Se quitaron los `<link>` a Google Fonts (Space Grotesk/Inter/IBM Plex Mono) de los 4 `index.html` — ya no se cargan archivos de fuente.
- **Fondo agrupado + tarjetas blancas** (`systemGroupedBackground` #F2F2F7 / `secondarySystemGroupedBackground` blanco), azul del sistema `#007AFF` como único acento de acción, verde/ámbar/rojo semánticos con fondos tintados al 12-14%.
- **Modo oscuro automático de verdad**: cada `App.css` tiene un bloque `@media (prefers-color-scheme: dark)` con los tokens oscuros de Apple (`#000000` / `#1C1C1E`, azul `#0A84FF`). Verificado en vivo: con el navegador del usuario en modo oscuro del sistema, la app cambió sola sin ningún flag ni prop.
- **Componentes**: control segmentado (`.segmented`/`.segment`/`.segment-active`, la pastilla blanca con sombra sutil) en vez de pestañas de píldora o subrayado; campos de texto rellenos sin borde (`background: fill quaternary`); botones sin sombra dura ni glow, solo color + opacidad al presionar (`:active { opacity:.75; transform: scale(.985) }`); números con `font-variant-numeric: tabular-nums` en vez de una tipografía monoespaciada aparte; separadores de 0.5px en vez de bordes de 1px.
- **Se eliminó** todo el lenguaje "ticket/folio" del intento anterior (`.folio-header`, códigos `R-XXXXXX`/`PLAN-XXXXXX`, eyebrows `REGISTRO · CLIENTE`) y el emoji de interfaz (cámara/candado/recibo) — quedó un set de íconos de trazo propio en `components/icons.jsx` (inspirado en SF Symbols, no son símbolos de Apple literales).
- **`apps/web` (landing)**: se quitó el plano técnico (SVG de casa), las categorías como "ticket" con folio y perforado, y los "stubs" de pasos — ahora es una landing con jerarquía tipográfica grande (headline 50px), tarjetas simples con sombra casi imperceptible, y una tarjeta de vista previa del producto (`.preview-card`) ilustrativa en vez de una foto real.
- **`apps/admin`**: ya usaba azul (`#1F6FEB`, sin naranja/navy — nunca tuvo el tratamiento "Orden de servicio"), así que fue la conversión más directa; el sidebar de pestañas pasó de píldora activa a fila con relleno azul tenue (como Ajustes/Mail de Apple).

### Verificación
`yarn build` OK en las 4 apps, **25/25 tests de cliente pasan sin cambios**. Capturas de pantalla en vivo confirmando: (1) el landing con contenido real de la API renderizando el hero/preview-card/categorías; (2) el cliente autenticado con una solicitud real, control segmentado y modo oscuro automático funcionando correctamente.

### Pendiente si se quiere seguir
- Repaso visual detallado de subpantallas profundas (chat, checkout de Stripe, tabla de reseñas en admin) — heredan el sistema por CSS pero no se retocaron a mano una por una.
- `apps/provider`: la lógica de negocio (chips de categoría, tabla de niveles, métricas) ya está convertida a tokens HIG pero no se verificó visualmente con captura (sin sesión de proveedor a mano en esta pasada).
- `ai_quote`: down-scale de imágenes (PIL) antes de enviar a Groq para grandes cargas.
- Preview: exponer también web/provider/admin (hoy solo cliente; se alterna con `PREVIEW_APP`).

## HIG con carácter: acento cálido + Space Grotesk (Sep 2026) — las 4 apps
Tercer rediseño de la sesión. El HIG puro de arriba (azul `#007AFF`, sin tipografía de marca) no convenció del todo: encuestado explícitamente, el usuario señaló "se siente frío / sin personalidad" — el problema no era la mecánica (segmented control, fondo agrupado, modo oscuro automático), sino la ejecución genérica de Apple. Petición: mantener el HIG como base estructural pero darle calidez y personalidad de marca, en **las 4 apps** (decisión de alcance repetida: "Todo, marca completa desde cero").

### Cambios sobre el HIG puro
- **Acento cálido propio**: `#FF6B47` (coral), deliberadamente distinto tanto del azul de Apple como del naranja de marca ya descartado (`#E8622C`, del intento "Orden de trabajo"). Reemplaza `--primary`/`--accent` en los 4 `App.css`, en modo claro y oscuro (`#FF8B63` en oscuro).
- **Neutros con temperatura cálida** en vez de gris frío: fondo `#F7F2EE` (vs. `#F2F2F7` de Apple), texto `#241C16` con opacidades cálidas en vez de negro/blanco puro con opacidad neutra.
- **Space Grotesk solo en titulares** (`h1,h2,h3,.brand-name` y los números grandes tipo `.quote-price`/`.reputation-score`/`.commission-pct`/`.metric-value`, vía variable `--font-headline: "Space Grotesk", var(--font-display)`), el resto del texto y controles se quedan en la tipografía del sistema — es la única fuente de Google Fonts que se volvió a cargar, con pesos 600/700 nada más.
- Se mantiene todo lo demás del HIG: segmented control, campos rellenos, `tabular-nums`, separadores de 0.5px, modo oscuro automático.

### Bug de rollout detectado por el usuario
Se implementó primero solo en `apps/client` como cheque de bajo costo antes de tocar las otras 3 apps (lección de la ronda anterior: no repetir cambios de alcance completo sin verificar primero). El usuario mandó una captura de la landing (`apps/web`) mostrando que seguía en el azul frío del HIG puro — **"pero la landing no se ve bonita"**. Corregido: se sincronizó la paleta cálida + Space Grotesk en `apps/web`, `apps/provider` y `apps/admin`. En `apps/web` además se recalentaron las sombras que estaban hardcodeadas en negro (`rgba(0,0,0,...)` → tintes cálidos/coral) y se añadió un glow radial cálido detrás del hero (`.hero::before`) para dar más riqueza visual a la landing, ya que es la página de marketing y tiene más margen para tratamiento decorativo que las apps internas.

### Verificación
`yarn build` OK en las 4 apps, **25/25 tests de cliente pasan sin cambios**. Captura de pantalla en vivo de la landing (`localhost:5176`, verificado con curl directo al dev server para evitar el caché del Simple Browser de VS Code) confirmando el hero con headline en Space Grotesk, CTA coral, pill "Servicio verificado" y el glow cálido detrás de la tarjeta de vista previa.

### Lección de proceso (para no repetir)
Cuando el alcance decidido es "las 4 apps", verificar con una captura de **cada** app (o al menos landing + una interna) antes de reportar terminado — hacer el cheque de bajo costo en una sola app y dar por hecho que el resto ya heredó el cambio fue lo que produjo el bug que el usuario tuvo que señalar.

## Selector de tema manual (Sep 2026) — las 4 apps
Al ver la paleta cálida en modo oscuro (su sistema está en oscuro), el usuario pidió explícitamente exponer un selector manual de tema ("quizás dejar los dos temas para poder hacer el cambio entre temas") además de aplicar la paleta cálida de forma consistente. Hasta este punto el modo oscuro solo se activaba automáticamente vía `prefers-color-scheme`, sin forma de forzarlo desde la UI.

### Implementación
- `src/theme.js` (uno por app, mismo contenido en las 4): `getStoredTheme`/`getSystemTheme` leen `localStorage["xambas-theme"]` y `matchMedia`; `setTheme`/`applyTheme` escriben el atributo `data-theme="light"|"dark"` en `<html>`; `initTheme()` se llama en `main.jsx` antes de montar React.
- Script inline en cada `index.html` (antes de que cargue nada más) que aplica `data-theme` desde `localStorage` de forma síncrona, para evitar un flash del tema equivocado en la primera pintura.
- `components/ThemeToggle.jsx` (uno por app): botón circular con ícono de sol/luna que alterna el tema y persiste la elección. Mientras no haya elección explícita, sigue el cambio de `prefers-color-scheme` del sistema en vivo.
- **Patrón CSS para que la elección explícita gane sobre el sistema**: el bloque `@media (prefers-color-scheme: dark)` pasa de `:root { ... }` a `:root:not([data-theme="light"]) { ... }`, y se agrega un bloque nuevo `:root[data-theme="dark"] { ... }` (mismos tokens, duplicados porque son hojas de estilo planas sin preprocesador). Así: sin elección → sigue al sistema; `data-theme="light"` fuerza claro aunque el sistema esté en oscuro; `data-theme="dark"` fuerza oscuro aunque el sistema esté en claro.
- `apps/web` (landing) no tenía modo oscuro en absoluto — se le creó un bloque de tokens oscuros (equivalentes cálidos a los de las otras 3 apps, mapeando `--paper`/`--ink`/`--accent`/etc.) además del toggle, para que el selector tenga algo que alternar.
- El botón vive en el header de cada app (`header-right` en client/provider/admin, `nav-actions` nuevo en web junto al menú hamburguesa), visible incluso antes de iniciar sesión.

### Verificación
`yarn build` OK en las 4 apps, 25/25 tests de cliente sin cambios. Verificado en vivo en `apps/admin`: el botón alterna correctamente entre el tema oscuro cálido y el tema claro cálido, con el ícono cambiando de luna a sol y el tooltip actualizándose ("Modo oscuro" / "Modo claro").

### Nota de herramienta (para no repetir)
Al tomar capturas de pantalla con PowerShell (`System.Drawing`/`CopyFromScreen`) en esta máquina, **siempre llamar primero a `user32.dll!SetProcessDPIAware()`** (vía un tipo C# inline). Sin eso, `Screen.PrimaryScreen.Bounds` y la captura devuelven la resolución virtualizada por Windows (en esta máquina 1536×864) en vez de la resolución física real (1920×1080), recortando silenciosamente el borde derecho de la pantalla — cualquier elemento de UI anclado a la derecha (como este selector de tema) parece no existir aunque el código esté perfectamente correcto. Cada invocación de PowerShell es un proceso nuevo, así que hay que llamar `SetProcessDPIAware()` en cada script de captura, no solo una vez por sesión.

## Notas de negocio (posicionamiento vs competencia)
Comisión escalonada por nivel ya modelada (`billing/tiers.py`). Servicios recurrentes refuerzan retención/lealtad (menor incentivo de fuga), alineado con la tesis del estudio.

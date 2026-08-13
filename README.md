# Xambas

Base inicial del marketplace de servicios del hogar y profesionales.

Esta etapa deja listo el monorepo para desarrollar:

- `backend` en `Python + FastAPI`
- `frontend cliente` en `React + Vite`
- `frontend proveedor` en `React + Vite`
- separacion logica de dominios: `identity`, `matching`, `billing`, `messaging`, `reputation`
- variables de entorno separadas para `development`, `staging` y `production`

## Estado actual

- Fase actual: `Fase 0 - Fundacion`
- Etapa completada: `Etapa 1 - Infraestructura base`
- Subetapa completada: `Subetapa 1.2 - MVP funcional end-to-end`
- Avance actual: flujo completo probado de punta a punta:
  registro (`bootstrap`) → verificacion `OTP` → catalogo de `categories` →
  creacion de `service_requests` con `matching` automatico → el proveedor ve
  sus oportunidades y acepta el `match` → chat (`messaging`) entre cliente y
  proveedor → el cliente deja una `review` → la reputacion del proveedor se
  actualiza automaticamente. Los frontends `client` y `provider` ya consumen
  la API real (no son mas placeholders estaticos).

## Estructura

```text
xambas/
  apps/
    api/
      app/
        core/
        modules/
          identity/
          matching/
          billing/
          messaging/
          reputation/
    client/
    provider/
  env/
    api/
    client/
    provider/
  infra/
    docker-compose.dev.yml
```

## Convenciones iniciales

- `apps/api` concentra la API Gateway del MVP.
- Cada dominio del backend vive en su propia carpeta y expone sus rutas sin depender del detalle interno de otros modulos.
- `billing` ya soporta una resolucion inicial multi-rail con `Stripe Connect` y `Mercado Pago`.
- `PAYMENTS_PROVIDER=auto` permite resolver el riel por pais; tambien puede fijarse manualmente a `stripe` o `mercado_pago`.
- `env/` centraliza templates de configuracion por aplicacion y por ambiente.

## Requisitos locales

- `Python 3.12+`
- `uv`
- `Node.js 22+`
- `corepack`
- `Docker Desktop`

## Setup local

1. Habilita Yarn:

```bash
corepack enable
```

2. Instala dependencias del frontend desde la raiz:

```bash
yarn install
```

3. Crea los archivos de entorno locales:

```powershell
Copy-Item env\api\.env.development.example apps\api\.env
Copy-Item env\client\.env.development.example apps\client\.env
Copy-Item env\provider\.env.development.example apps\provider\.env
```

4. Levanta MongoDB:

```bash
docker compose -f infra/docker-compose.dev.yml up -d
```

5. Prepara el backend:

```bash
cd apps/api
uv venv
uv sync
```

6. Ejecuta la API:

```bash
cd apps/api
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. Ejecuta el frontend cliente:

```bash
yarn dev:client
```

8. Ejecuta el frontend proveedor:

```bash
yarn dev:provider
```

## Endpoints iniciales

- `GET /health`
- `GET /api/identity/status`
- `POST /api/identity/bootstrap`
- `GET /api/identity/users/{user_id}`
- `POST /api/identity/otp/request`
- `POST /api/identity/otp/verify`
- `GET /api/matching/status`
- `POST /api/matching/categories`
- `GET /api/matching/categories`
- `GET /api/matching/categories/{category_id}`
- `POST /api/matching/service-requests`
- `GET /api/matching/service-requests`
- `GET /api/matching/service-requests/{request_id}`
- `POST /api/matching/service-requests/{request_id}/run`
- `GET /api/matching/service-requests/{request_id}/matches`
- `GET /api/matching/providers/{provider_user_id}/matches`
- `POST /api/matching/matches/{match_id}/accept`
- `GET /api/billing/status`
- `GET /api/billing/provider?country_code=MX`
- `GET /api/messaging/status`
- `POST /api/messaging/threads` — obtiene o crea el hilo de chat asociado a un `match_id`
- `GET /api/messaging/threads/{thread_id}/messages`
- `POST /api/messaging/threads/{thread_id}/messages`
- `GET /api/reputation/status`
- `POST /api/reputation/reviews` — una resena por `client_id` + `request_id`; recalcula `rating_avg` del proveedor
- `GET /api/reputation/providers/{provider_profile_id}`
- `GET /api/admin/status`
- `POST /api/admin/auth/bootstrap` — crea el primer administrador (`super_admin`); solo funciona una vez
- `POST /api/admin/auth/login`
- `GET /api/admin/auth/me`
- `POST /api/admin/admins` / `GET /api/admin/admins` — solo `super_admin`
- `POST /api/admin/categories` / `PATCH /api/admin/categories/{id}`
- `GET /api/admin/users` / `PATCH /api/admin/users/{id}` — rol, `kyc_status`, `is_active`
- `GET /api/admin/providers` / `PATCH /api/admin/providers/{id}` — `tier`, verificaciones, `is_active`
- `GET /api/admin/service-requests` — supervision de todas las solicitudes
- `GET /api/admin/reviews` / `DELETE /api/admin/reviews/{id}` — moderacion, recalcula el rating del proveedor
- `GET /api/content/site` (publico) / `PUT /api/content/site` (admin) — marca y contenido del landing
- `GET /api/content/business` / `PUT /api/content/business` (admin) — comision, pagos habilitados, parametros de matching
- `GET /api/billing/tiers` — niveles de proveedor y su comision (publico)
- `GET /api/billing/commission/quote?provider_profile_id=&job_amount=` — cotizacion real para un proveedor y un monto de trabajo
- `POST /api/billing/payments` — crea el `PaymentIntent` en Stripe para un match `accepted` (deposito completo, retenido)
- `GET /api/billing/payments/{id}` — consulta un pago (sincroniza el estado contra Stripe si sigue `pending`)
- `GET /api/billing/payments?client_id=` / `?provider_user_id=` — historial de pagos
- `POST /api/billing/payments/{id}/confirm-completion?client_id=` — el cliente confirma el trabajo y se transfieren los fondos al proveedor (Stripe Connect)
- `POST /api/billing/payments/{id}/refund` (admin) — reembolsa un pago `pending` o `held_in_escrow`
- `GET /api/billing/admin/payments` (admin) — todos los pagos
- `POST /api/billing/connect/onboarding-link` — crea (si no existe) la cuenta conectada de Stripe del proveedor y devuelve el link de onboarding
- `GET /api/billing/connect/status?provider_profile_id=` — estado de verificacion de la cuenta conectada
- `POST /api/billing/webhooks/stripe` — receptor de webhooks de Stripe (fuente de verdad en produccion)

Todas las rutas `/api/admin/*` y los `PUT` de `/api/content/*` requieren el header `Authorization: Bearer <token>` obtenido en el login del admin.

## Pagos en custodia (Stripe Connect) — ya conectado, no solo modelado

A diferencia de la primera version (donde `business_settings` solo
guardaba la comision sin efecto real), esto **si mueve dinero de
verdad en modo test** contra tu cuenta de Stripe:

1. **Deposito**: el cliente paga el monto completo (`job_amount` +
   tarifa de servicio) via `PaymentIntent` en cuanto el `match` esta
   `accepted`. El dinero queda en la cuenta de la plataforma, no en la
   del proveedor todavia -- eso es la custodia.
2. **Confirmacion via webhook**: `payment_intent.succeeded` mueve el
   pago a `held_in_escrow`.
3. **Liberacion**: cuando el cliente confirma que el trabajo esta
   terminado (`POST /payments/{id}/confirm-completion`), se crea un
   `Transfer` de Stripe Connect hacia la cuenta conectada del
   proveedor por `provider_receives` (el monto ya sin la comision de
   la plataforma). Si el proveedor no ha completado el onboarding de
   Stripe Connect, la liberacion se rechaza con un mensaje claro en
   vez de fallar en silencio.
4. **Proveedores**: deben completar `POST /connect/onboarding-link`
   (crea su cuenta Express de Stripe si no existe) y terminar el
   formulario de verificacion que Stripe aloja.

### Ya conectado al frontend

- **Cliente** (`apps/client`): en cada match `accepted` aparece "Pagar y
  reservar" → formulario de monto → checkout con Stripe Elements
  (`@stripe/react-stripe-js`) embebido en la misma pantalla → una vez
  pagado, ve el estado (`pending` / `held_in_escrow` / `released`) y el
  boton "Confirmar trabajo terminado y liberar pago".
- **Proveedor** (`apps/provider`): seccion "Cobros" con el estado de su
  cuenta de Stripe Connect (con boton de onboarding si falta) y su
  historial de pagos recibidos.

### Como probarlo en tu maquina

```powershell
# 1. Instala el Stripe CLI y logueate
stripe login

# 2. Reenvia los webhooks a tu API local (deja esto corriendo aparte)
stripe listen --forward-to localhost:8000/api/billing/webhooks/stripe
# copia el "whsec_..." que imprime y ponlo en apps/api/.env como STRIPE_WEBHOOK_SECRET

# 3. Corre deploy.bat normalmente
```

Con tarjetas de prueba de Stripe (ej. `4242 4242 4242 4242`) puedes
completar el flujo real de deposito -> custodia -> liberacion sin
mover dinero real. **Nota**: yo no pude probar contra la API real de
Stripe desde este entorno (sin acceso de red a `api.stripe.com`); lo
que si valide exhaustivamente es toda la logica de negocio alrededor
(maquina de estados, autorizacion, calculo de montos, idempotencia)
sustituyendo el cliente de Stripe por un doble de prueba. La llamada
real a Stripe queda por confirmar en tu maquina.

Lo que **todavia falta** de esta pieza: pagos por etapas (milestones)
para proyectos grandes, y un flujo de disputa/reversal para pagos ya
`released` (hoy el reembolso solo cubre `pending`/`held_in_escrow`).

## Diferenciadores frente a la competencia (del estudio de mercado)

Se incorporaron dos hallazgos centrales del estudio adjunto
(`Marketplace_Servicios_Investigacion_y_Diseno`) que atacan la causa
raiz de abandono documentada en Thumbtack/Angi/Bark:

- **Comision escalonada por nivel** (`app/modules/billing/tiers.py`):
  Nuevo (10%) -> Plata (9%) -> Oro (7.5%) -> Platino (6%), mas una
  tarifa de servicio al cliente del 5% (minimo $3, techo $250). El
  proveedor paga solo cuando el trabajo se confirma y se paga, nunca
  por cada contacto -- lo opuesto al pago-por-lead que el estudio
  identifica como la causa #1 de insatisfaccion. Los porcentajes estan
  marcados `[SUPUESTO]` en el estudio original: deben calibrarse con
  pruebas de mercado antes de fijarse en produccion.
- **Sistema anti-fuga en el chat** (`app/modules/messaging/leak_detection.py`):
  detecta y redacta con un bloqueo suave (no silencioso) intentos de
  compartir telefono, correo (incluyendo "arroba"/"punto"), enlaces
  externos y menciones de redes sociales -- incluso telefonos
  deletreados ("cinco cinco cinco..."). El contacto real se libera
  automaticamente cuando el `match` pasa a `accepted` (proxy de
  "deposito confirmado" hasta que exista un motor de pagos real). El
  diseno es deliberadamente tolerante: el propio estudio advierte que
  un sistema demasiado agresivo empuja a evadirlo con mas
  sofisticacion en vez de reducir la fuga real.

Lo que el estudio recomienda y **todavia no existe**: pagos por
etapas (milestones) para proyectos grandes, y el panel de negocio
completo del proveedor (CRM, facturacion). El pago en custodia
(escrow) ya se implemento con Stripe Connect -- ver la seccion
"Pagos en custodia" arriba.

La documentacion interactiva (Swagger) queda disponible en `http://localhost:8000/docs` mientras la API corre.

## OTP y Sesion

- `development` usa `OTP_PROVIDER=dev` y puede exponer `debug_code` para pruebas locales.
- `staging` y `production` quedan preparados para `OTP_PROVIDER=twilio`.
- La integracion real usa `Twilio Verify` con:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_VERIFY_SERVICE_SID`
- El backend mantiene politica local de intentos con `OTP_MAX_ATTEMPTS`.
- Las sesiones se crean solo despues de una verificacion OTP exitosa.

## Categorias de Lanzamiento

El catalogo inicial se siembra automaticamente al arrancar la API.

- `Limpieza del Hogar` - `pricing_mode=fixed` - `risk_level=standard`
- `Plomeria` - `pricing_mode=quote` - `risk_level=standard`
- `Electricidad` - `pricing_mode=quote` - `risk_level=regulated`
- `Montaje de Muebles` - `pricing_mode=fixed` - `risk_level=standard`

Subcategorias iniciales:

- Limpieza: `Limpieza Basica`, `Limpieza Profunda`, `Limpieza de Mudanza`
- Plomeria: `Fugas`, `Destapes`, `Instalaciones`, `Reparaciones Generales`
- Electricidad: `Reparaciones Electricas`, `Instalaciones Electricas`, `Iluminacion`, `Tablero Electrico`
- Montaje de Muebles: `Ropero`, `Cama`, `Escritorio`, `Centro de Entretenimiento`

## Matching Inicial

- `service_requests` crea la solicitud del cliente y hereda `pricing_mode` y `risk_level` desde la categoria seleccionada.
- El matching inicial busca proveedores por `category_id` y `coverage_zone`.
- Para subcategorias, el motor tambien acepta proveedores registrados en la categoria padre.
- El score actual prioriza:
  - coincidencia exacta de categoria
  - cobertura en la zona solicitada
  - rating y trabajos completados
  - verificaciones de seguro y licencia
- En categorias `regulated`, el proveedor necesita `license_verified=true` para entrar al matching.
- Si hay candidatos, la solicitud pasa a estado `matched`; si no, permanece en `open`.

## Pagina publica (apps/web)

Landing de marketing (puerto `5176` en dev, `4176` en preview). Sin
autenticacion — consume `GET /api/content/site` (publico) y
`GET /api/matching/categories` para mostrar marca, hero, "como funciona" y
categorias destacadas en vivo, tal cual se configuran desde `apps/admin`.
Los botones "Publicar solicitud" / "Soy proveedor" enlazan a `apps/client`
y `apps/provider` via `VITE_CLIENT_URL` / `VITE_PROVIDER_URL`.

Si `GET /api/content/site` falla (API caida), la pagina muestra un
contenido de respaldo embebido en el codigo en vez de romperse.

### Sistema de diseno: "Orden de servicio"

En vez de un look generico de SaaS, la landing usa un lenguaje visual
literal al oficio: el plano tecnico y el ticket de trabajo.

- **Paleta**: papel `#EEF0F2`, azul plano `#1B3A5C`, naranja de
  seguridad `#E8622C` (el mismo naranja de obra/herramienta, no un
  acento generico), verde de verificacion `#2F7A4D`.
- **Tipografia**: `Space Grotesk` para titulos (tecnica, con caracter),
  `Inter` para texto, `IBM Plex Mono` para numeros de ticket, precios y
  codigos de categoria — refuerza la idea de "orden de trabajo".
- **Elemento firma**: el hero incluye un plano lineal (SVG) de una casa
  con pines numerados sobre un fondo de cuadricula de plano tecnico, en
  vez de una foto de stock generica.
- **Categorias como tickets**: cada categoria se muestra con un codigo
  tipo folio (`N.01`, `N.02`...) y borde tipo cupon perforado.
- La barra de confianza del hero usa afirmaciones reales del producto
  (pago en custodia, chat anti-fuga, niveles verificados) en vez de
  testimonios inventados.

Los tokens de color y tipografia (`Space Grotesk` + la paleta azul/
naranja) tambien se aplicaron a `apps/client` y `apps/provider` para
que la marca sea consistente en todo el embudo, sin rehacer sus
layouts funcionales.

## Nota sobre MongoDB en Windows: conflicto de puerto 27017

Si ya tienes un MongoDB nativo instalado como servicio de Windows, va a
competir por el puerto `27017` con el contenedor Docker — la API se
conecta entonces al Mongo equivocado (sin las credenciales `root/root`) y
falla con `Authentication failed` aunque el contenedor este bien
configurado. Por eso `infra/docker-compose.dev.yml` publica el contenedor
en el puerto `27018` del host (`27018:27017`) y `MONGO_URI` en
`apps/api/.env` apunta a `mongodb://root:root@localhost:27018/...`. Si
tu maquina no tiene ese conflicto, puedes regresarlo a `27017` sin
problema.

## Frontends (client y provider)

Ambas apps son React + Vite y ya hablan con la API real (sin dependencias
nuevas, solo `react`/`react-dom`, para no romper el lockfile de Yarn):

- **client** (`apps/client`): registro (`bootstrap` + verificacion `OTP`),
  explorar categorias, crear una `service_request`, ver los `matches`
  sugeridos, chatear con el proveedor y dejar una resena una vez que el
  match esta `accepted`.
- **provider** (`apps/provider`): registro con perfil de negocio
  (`business_name`, categorias, zonas de cobertura, seguro/licencia),
  bandeja de oportunidades (`matches` asignados), aceptar un trabajo, chat
  con el cliente y panel de reputacion (`rating_avg`, `jobs_completed`,
  resenas recibidas).

La sesion se guarda en `localStorage` del navegador (`xambas_client_session`
/ `xambas_provider_session`). Como todavia no existe un endpoint de login
por telefono, "iniciar sesion" en este MVP equivale a volver a entrar con
la sesion guardada; "Cerrar sesion" limpia el `localStorage` y permite
simular otro usuario.

En `development`, `OTP_PROVIDER=dev` regresa `debug_code` en la respuesta
de `POST /api/identity/otp/request`, y la UI lo muestra directamente en
pantalla para poder probar el flujo sin un SMS real.

## Panel de administrador (apps/admin)

Tercera app React + Vite (puerto `5175` en dev, `4175` en preview de `deploy.bat`).
Al entrar por primera vez, si no existe ningun administrador, la pantalla de
login se convierte en "crear el primer administrador" (`super_admin`). Desde
ahi se gestiona:

- **Categorias**: crear y editar (nombre, modo de precio, nivel de riesgo).
- **Usuarios**: rol, estado de KYC, activar/desactivar cuenta.
- **Proveedores**: tier, verificacion de seguro/licencia, activar/desactivar.
- **Solicitudes**: supervision de todas las `service_requests` (solo lectura).
- **Resenas**: moderacion — borrar una resena recalcula el `rating_avg` del
  proveedor desde cero con las resenas restantes.
- **Contenido del sitio**: marca (nombre, logo, colores) y landing (hero,
  pasos de "como funciona", categorias destacadas) — esto es lo que
  consumira `apps/web` cuando se construya.
- **Negocio**: comision, metodos de pago habilitados por pais, parametros
  de matching (resultados maximos, score minimo).
- **Administradores** (solo `super_admin`): crear cuentas adicionales con
  rol `editor` o `super_admin`.

No hay "editor visual" de diseño (arrastrar bloques): es un formulario
estructurado. Esto es deliberado — mantiene el sitio publico simple y
rapido de construir; si mas adelante se necesita un editor libre de
bloques, es un proyecto aparte.

## CORS y puertos

- La API expone `CORSMiddleware` usando la lista de `CORS_ORIGINS` del
  `.env` (incluye `5173`-`5176` para `vite dev` de client/provider/admin/web
  y `4173`-`4176` para `vite preview`, que es lo que sirve `deploy.bat`).
- `BACKEND_PORT` en `deploy.bat` / `deploy.sh` esta alineado a `8000`, el
  mismo puerto que usan `apps/api/.env` y `VITE_API_BASE_URL` en los
  frontends. Si cambias el puerto de la API, actualiza los tres lugares.

## Siguientes pasos sugeridos

1. Conectar `business_settings` de verdad a `billing`/`matching` (hoy se guarda pero `matching`/`billing` aun usan sus propias constantes).
2. Agregar filtros avanzados al matching: disponibilidad, radio, SLA, urgencia y reputacion por categoria.
3. Endpoint de login real (OTP por telefono sin bootstrap) para no depender solo de `localStorage`.
4. Notificaciones en tiempo real para mensajes nuevos (websockets o polling) en vez de refresco manual.
5. SEO basico para `apps/web` (meta tags dinamicos, sitemap) si se va a indexar en buscadores.

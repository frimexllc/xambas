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
- Subetapa completada: `Subetapa 1.1 - Repositorios y entornos`
- Avance actual: base tecnica inicial de `billing`, `identity` con persistencia, OTP y sesion base usando `dev` o `Twilio Verify`, catalogo configurable de `categories` con seed inicial y primer flujo de `service_requests` + `matches`

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
- `GET /api/billing/status`
- `GET /api/billing/provider?country_code=MX`
- `GET /api/messaging/status`
- `GET /api/reputation/status`

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

## Siguientes pasos sugeridos

1. Implementar el `billing_engine` como fuente unica de verdad para comision, payout y revenue.
2. Agregar filtros avanzados al matching: disponibilidad, radio, SLA, urgencia y reputacion por categoria.
3. Agregar seeds o backoffice para administrar el catalogo sin tocar codigo.
4. Conectar mensajeria interna y, mas adelante, `Twilio Proxy` para numeros enmascarados.

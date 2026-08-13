#!/bin/bash
set -uo pipefail

# ==========================================================
#  xambas - Deploy (Linux/Mac)
#  Estructura: apps/client, apps/provider (yarn workspaces)
#              apps/api (Python FastAPI, fuera de los workspaces)
#              env/{api,client,provider}  ->  apps/{api,client,provider}/.env
#              infra/docker-compose.dev.yml (MongoDB)
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$ROOT_DIR/apps/api"
CLIENT_DIR="$ROOT_DIR/apps/client"
PROVIDER_DIR="$ROOT_DIR/apps/provider"
ADMIN_DIR="$ROOT_DIR/apps/admin"
WEB_DIR="$ROOT_DIR/apps/web"
ENV_DIR="$ROOT_DIR/env"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.dev.yml"

# Ajusta esto si tu ambiente por defecto no es "development"
ENVIRONMENT="${ENVIRONMENT:-development}"

BACKEND_PORT=8000
CLIENT_PREVIEW_PORT=4173
PROVIDER_PREVIEW_PORT=4174
ADMIN_PREVIEW_PORT=4175
WEB_PREVIEW_PORT=4176

# Si el auto-detect del entry point de FastAPI falla, ponlo aquí manualmente
# p.ej. APP_MODULE_OVERRIDE="app.main:app"
APP_MODULE_OVERRIDE=""

echo "========================================"
echo "  xambas - Deploy (Linux/Mac)"
echo "========================================"
echo ""

command_exists() { command -v "$1" >/dev/null 2>&1; }

# ---------- 0. Pre-flight checks ----------
info "Checking prerequisites..."

if ! command_exists node; then
    error "Node.js is not installed. Install from https://nodejs.org"
    exit 1
fi
info "Node.js found: $(node -v)"

if ! command_exists python3; then
    error "Python3 is not installed. Install via: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
info "Python found: $(python3 --version)"

# packageManager está fijado a yarn@4.9.1 (Berry). Si hay un yarn classic
# global instalado, forzamos el uso de la versión correcta vía corepack
# para evitar conflictos de lockfile / resolución de workspaces.
if command_exists corepack; then
    corepack enable >/dev/null 2>&1 || warn "corepack enable falló (puede requerir sudo). Intentando continuar de todas formas."
    YARN_CMD="corepack yarn"
    info "Usando corepack para forzar yarn@4.9.1 (evita conflicto con yarn classic global)."
else
    warn "corepack no encontrado. Se usará el 'yarn' del PATH; si es v1.x puede haber conflictos con el lockfile de Berry."
    if ! command_exists yarn; then
        error "yarn no está instalado y corepack no está disponible."
        exit 1
    fi
    YARN_CMD="yarn"
fi
info "Yarn: $($YARN_CMD --version 2>/dev/null || echo 'version check falló, continuando')"

if command_exists docker; then
    info "Docker found: $(docker --version)"
else
    warn "Docker no encontrado. MongoDB no se levantará automáticamente; asegúrate de tenerlo corriendo por otro medio."
fi

# ---------- 1. Copiar archivos .env desde env/ si faltan ----------
echo ""
info "Verificando archivos .env (ambiente: $ENVIRONMENT)..."

copy_env_if_missing() {
    local app_name="$1"
    local app_dir="$2"
    local src_dev="$ENV_DIR/$app_name/.env.$ENVIRONMENT.example"
    local src_generic="$ENV_DIR/$app_name/.env.example"

    if [ -f "$app_dir/.env" ]; then
        info "apps/$app_name/.env ya existe, no se toca."
        return
    fi

    if [ -f "$src_dev" ]; then
        cp "$src_dev" "$app_dir/.env"
        warn "Copiado $src_dev -> apps/$app_name/.env. Revisa secretos antes de producción."
    elif [ -f "$src_generic" ]; then
        cp "$src_generic" "$app_dir/.env"
        warn "Copiado $src_generic -> apps/$app_name/.env. Revisa secretos antes de producción."
    else
        warn "No se encontró plantilla .env para '$app_name' en env/$app_name/. Deberás crear apps/$app_name/.env manualmente."
    fi
}

copy_env_if_missing "api" "$API_DIR"
copy_env_if_missing "client" "$CLIENT_DIR"
copy_env_if_missing "provider" "$PROVIDER_DIR"
copy_env_if_missing "admin" "$ADMIN_DIR"
copy_env_if_missing "web" "$WEB_DIR"

# ---------- 2. Levantar MongoDB (docker compose) ----------
echo ""
if command_exists docker && [ -f "$COMPOSE_FILE" ]; then
    info "Levantando MongoDB con docker compose..."
    if docker compose version >/dev/null 2>&1; then
        docker compose -f "$COMPOSE_FILE" up -d
    elif command_exists docker-compose; then
        docker-compose -f "$COMPOSE_FILE" up -d
    else
        warn "No se encontró 'docker compose' ni 'docker-compose'. Omitiendo."
    fi
else
    warn "Omitiendo levantamiento de MongoDB (docker o docker-compose.dev.yml no disponibles)."
fi

# ---------- 3. Liberar puertos que vamos a usar ----------
free_port() {
    local port="$1"
    if command_exists lsof; then
        local pid
        pid=$(lsof -ti tcp:"$port" || true)
        if [ -n "${pid:-}" ]; then
            warn "Puerto $port en uso (PID $pid). Liberando..."
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
    fi
}
free_port "$BACKEND_PORT"
free_port "$CLIENT_PREVIEW_PORT"
free_port "$PROVIDER_PREVIEW_PORT"
free_port "$ADMIN_PREVIEW_PORT"
free_port "$WEB_PREVIEW_PORT"

# ---------- 4. Instalar dependencias de los workspaces (client + provider) ----------
echo ""
info "[1/3] Instalando dependencias del monorepo (client + provider)..."
cd "$ROOT_DIR"

if ! $YARN_CMD install; then
    warn "yarn install falló - limpiando node_modules/caché y reintentando..."
    rm -rf node_modules apps/client/node_modules apps/provider/node_modules
    rm -rf .yarn/install-state.gz .yarn/cache
    if ! $YARN_CMD install; then
        error "La instalación de dependencias falló incluso después de limpiar."
        exit 1
    fi
fi

# ---------- 5. Build de client, provider y admin ----------
info "[2/3] Compilando client, provider y admin..."
if ! $YARN_CMD run build:client; then
    error "Build de 'client' falló."
    exit 1
fi
if ! $YARN_CMD run build:provider; then
    error "Build de 'provider' falló."
    exit 1
fi
if ! $YARN_CMD run build:admin; then
    error "Build de 'admin' falló."
    exit 1
fi
if ! $YARN_CMD run build:web; then
    error "Build de 'web' falló."
    exit 1
fi

# ---------- 6. Backend Python (apps/api) ----------
echo ""
info "[3/3] Configurando backend (apps/api)..."
cd "$API_DIR" || { error "apps/api no encontrado"; exit 1; }

if [ ! -f requirements.txt ]; then
    error "apps/api/requirements.txt no encontrado"
    exit 1
fi

if [ ! -d venv ]; then
    info "Creando entorno virtual de Python..."
    python3 -m venv venv || { error "No se pudo crear el venv"; exit 1; }
fi

# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip --quiet

if ! pip install -r requirements.txt --quiet; then
    warn "Conflicto de dependencias detectado - reintentando con --no-cache-dir..."
    if ! pip install -r requirements.txt --no-cache-dir; then
        error "La instalación de dependencias del backend falló."
        deactivate
        exit 1
    fi
fi

# Auto-detección del módulo de entrada de FastAPI
if [ -n "$APP_MODULE_OVERRIDE" ]; then
    API_MODULE="$APP_MODULE_OVERRIDE"
elif [ -f "server.py" ]; then
    API_MODULE="server:app"
elif [ -f "main.py" ]; then
    API_MODULE="main:app"
elif [ -f "app/main.py" ]; then
    API_MODULE="app.main:app"
else
    error "No se pudo detectar el entry point de FastAPI en apps/api."
    error "Edita APP_MODULE_OVERRIDE al inicio de este script (ej: \"app.main:app\")."
    deactivate
    exit 1
fi
info "Entry point detectado: $API_MODULE"

info "Iniciando uvicorn en el puerto $BACKEND_PORT..."
uvicorn "$API_MODULE" --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!
cd "$ROOT_DIR"

# ---------- 7. Servir los builds de client y provider ----------
info "Sirviendo build de 'client' en el puerto $CLIENT_PREVIEW_PORT..."
(cd "$CLIENT_DIR" && $YARN_CMD vite preview --port "$CLIENT_PREVIEW_PORT" --host) &
CLIENT_PID=$!

info "Sirviendo build de 'provider' en el puerto $PROVIDER_PREVIEW_PORT..."
(cd "$PROVIDER_DIR" && $YARN_CMD vite preview --port "$PROVIDER_PREVIEW_PORT" --host) &
PROVIDER_PID=$!

info "Sirviendo build de 'admin' en el puerto $ADMIN_PREVIEW_PORT..."
(cd "$ADMIN_DIR" && $YARN_CMD vite preview --port "$ADMIN_PREVIEW_PORT" --host) &
ADMIN_PID=$!

info "Sirviendo build de 'web' en el puerto $WEB_PREVIEW_PORT..."
(cd "$WEB_DIR" && $YARN_CMD vite preview --port "$WEB_PREVIEW_PORT" --host) &
WEB_PID=$!

echo ""
echo "========================================"
echo "  Deploy completo!"
echo "========================================"
echo ""
echo "Backend (FastAPI):  http://localhost:$BACKEND_PORT   (PID: $BACKEND_PID)"
echo "Client:              http://localhost:$CLIENT_PREVIEW_PORT   (PID: $CLIENT_PID)"
echo "Provider:            http://localhost:$PROVIDER_PREVIEW_PORT   (PID: $PROVIDER_PID)"
echo "Admin:               http://localhost:$ADMIN_PREVIEW_PORT   (PID: $ADMIN_PID)"
echo "Web:                 http://localhost:$WEB_PREVIEW_PORT   (PID: $WEB_PID)"
echo ""
echo "Para detener todo: kill $BACKEND_PID $CLIENT_PID $PROVIDER_PID $ADMIN_PID $WEB_PID"
echo ""

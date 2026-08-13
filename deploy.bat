@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   xambas - Deploy (Windows)
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
set "API_DIR=%ROOT_DIR%apps\api"
set "CLIENT_DIR=%ROOT_DIR%apps\client"
set "PROVIDER_DIR=%ROOT_DIR%apps\provider"
set "ADMIN_DIR=%ROOT_DIR%apps\admin"
set "WEB_DIR=%ROOT_DIR%apps\web"
set "ENV_DIR=%ROOT_DIR%env"
set "COMPOSE_FILE=%ROOT_DIR%infra\docker-compose.dev.yml"

REM Ajusta esto si tu ambiente por defecto no es "development"
if not defined ENVIRONMENT set "ENVIRONMENT=development"

set BACKEND_PORT=8000
set CLIENT_PREVIEW_PORT=4173
set PROVIDER_PREVIEW_PORT=4174
set ADMIN_PREVIEW_PORT=4175
set WEB_PREVIEW_PORT=4176

REM Si el auto-detect del entry point de FastAPI falla, ponlo aqui manualmente
REM p.ej. set "APP_MODULE_OVERRIDE=app.main:app"
set "APP_MODULE_OVERRIDE="

REM ---------- 0. Pre-flight checks ----------
echo [INFO] Checking prerequisites...

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed. Download it from https://nodejs.org
    exit /b 1
)
for /f "delims=" %%v in ('node -v') do echo [INFO] Node.js found: %%v

set "PY_CMD="
where python >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
) else (
    where py >nul 2>nul
    if not errorlevel 1 set "PY_CMD=py"
)
if not defined PY_CMD (
    echo [ERROR] Python is not installed. Download it from https://www.python.org/downloads/
    exit /b 1
)
for /f "delims=" %%v in ('%PY_CMD% --version') do echo [INFO] Python found: %%v

REM packageManager esta fijado a yarn@4.9.1 (Berry). Si hay un yarn classic
REM global instalado (como 1.22.22), usamos "corepack yarn" para forzar la
REM version correcta SIN necesitar "corepack enable" (que requiere permisos
REM de administrador y no hace falta: corepack puede ejecutar el paquete
REM pinneado directamente).
REM Evita prompts interactivos si corepack necesita descargar yarn@4.9.1:
set "COREPACK_ENABLE_DOWNLOAD_PROMPT=0"

set "PKGMGR=yarn"
where corepack >nul 2>nul
if not errorlevel 1 (
    set "PKGMGR=corepack yarn"
    echo [INFO] Usando "corepack yarn" para forzar yarn@4.9.1 ^(evita conflicto con yarn classic global^).
) else (
    echo [WARN] corepack no encontrado. Se usara el 'yarn' del PATH; si es v1.x puede haber conflictos con el lockfile de Berry.
    where yarn >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] yarn no esta instalado y corepack no esta disponible.
        exit /b 1
    )
)
echo [DEBUG] Checkpoint: deteccion de yarn/corepack OK.

where docker >nul 2>nul
set "DOCKER_READY=0"
if not errorlevel 1 (
    docker info >nul 2>nul
    if errorlevel 1 (
        echo [WARN] Docker esta instalado pero el daemon no esta corriendo ^(¿abriste Docker Desktop?^). Se omitira MongoDB.
    ) else (
        for /f "delims=" %%v in ('docker --version') do echo [INFO] Docker found: %%v
        set "DOCKER_READY=1"
    )
) else (
    echo [WARN] Docker no encontrado. MongoDB no se levantara automaticamente.
)
echo [DEBUG] Checkpoint: verificacion de Docker OK.

REM ---------- 1. Copiar archivos .env desde env/ si faltan ----------
echo.
echo [INFO] Verificando archivos .env (ambiente: %ENVIRONMENT%)...

call :copy_env api "%API_DIR%"
call :copy_env client "%CLIENT_DIR%"
call :copy_env provider "%PROVIDER_DIR%"
call :copy_env admin "%ADMIN_DIR%"
call :copy_env web "%WEB_DIR%"
goto after_env_functions

:copy_env
set "APP_NAME=%~1"
set "APP_DIR=%~2"
if exist "%APP_DIR%\.env" (
    echo [INFO] apps\%APP_NAME%\.env ya existe, no se toca.
    goto :eof
)
if exist "%ENV_DIR%\%APP_NAME%\.env.%ENVIRONMENT%.example" (
    copy "%ENV_DIR%\%APP_NAME%\.env.%ENVIRONMENT%.example" "%APP_DIR%\.env" >nul
    echo [WARN] Copiado env\%APP_NAME%\.env.%ENVIRONMENT%.example -^> apps\%APP_NAME%\.env. Revisa secretos.
    goto :eof
)
if exist "%ENV_DIR%\%APP_NAME%\.env.example" (
    copy "%ENV_DIR%\%APP_NAME%\.env.example" "%APP_DIR%\.env" >nul
    echo [WARN] Copiado env\%APP_NAME%\.env.example -^> apps\%APP_NAME%\.env. Revisa secretos.
    goto :eof
)
echo [WARN] No se encontro plantilla .env para '%APP_NAME%'. Crea apps\%APP_NAME%\.env manualmente.
goto :eof

:after_env_functions
echo [DEBUG] Checkpoint: archivos .env verificados/copiados OK.

REM ---------- 2. Levantar MongoDB (docker compose) ----------
echo.
if "%DOCKER_READY%"=="1" (
    if exist "%COMPOSE_FILE%" (
        echo [INFO] Levantando MongoDB con docker compose...
        docker compose -f "%COMPOSE_FILE%" up -d
        if errorlevel 1 (
            echo [WARN] 'docker compose' fallo, intentando 'docker-compose'...
            docker-compose -f "%COMPOSE_FILE%" up -d
        )
    ) else (
        echo [WARN] No se encontro infra\docker-compose.dev.yml. Omitiendo.
    )
) else (
    echo [WARN] Omitiendo levantamiento de MongoDB ^(Docker no disponible o Docker Desktop no esta corriendo^).
    echo [WARN] Si tu apps\api necesita MongoDB, abre Docker Desktop y vuelve a correr este script.
)
echo [DEBUG] Checkpoint: MongoDB (docker compose) OK.

REM ---------- 3. Liberar puertos que vamos a usar ----------
call :free_port %BACKEND_PORT%
call :free_port %CLIENT_PREVIEW_PORT%
call :free_port %PROVIDER_PREVIEW_PORT%
call :free_port %ADMIN_PREVIEW_PORT%
call :free_port %WEB_PREVIEW_PORT%
goto after_port_functions

:free_port
set "PORT=%~1"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo [WARN] Puerto %PORT% en uso ^(PID %%p^). Liberando...
    taskkill /F /PID %%p >nul 2>nul
)
goto :eof

:after_port_functions
echo [DEBUG] Checkpoint: puertos liberados OK.

REM ---------- 4. Instalar dependencias de los workspaces (client + provider) ----------
echo.
echo [1/3] Instalando dependencias del monorepo ^(client + provider^)...
cd /d "%ROOT_DIR%"

call %PKGMGR% install
if errorlevel 1 (
    echo [WARN] yarn install fallo - limpiando node_modules/cache y reintentando...
    rmdir /s /q node_modules 2>nul
    rmdir /s /q apps\client\node_modules 2>nul
    rmdir /s /q apps\provider\node_modules 2>nul
    rmdir /s /q .yarn\cache 2>nul
    del /f /q .yarn\install-state.gz 2>nul
    call %PKGMGR% install
    if errorlevel 1 (
        echo [ERROR] La instalacion de dependencias fallo incluso despues de limpiar.
        exit /b 1
    )
)

REM ---------- 5. Build de client y provider ----------
echo [2/3] Compilando client y provider...
call %PKGMGR% run build:client
if errorlevel 1 (
    echo [ERROR] Build de 'client' fallo.
    exit /b 1
)
call %PKGMGR% run build:provider
call %PKGMGR% run build:admin
call %PKGMGR% run build:web
if errorlevel 1 (
    echo [ERROR] Build de 'provider' fallo.
    exit /b 1
)

REM ---------- 6. Backend Python (apps/api) ----------
echo.
echo [3/3] Configurando backend ^(apps\api^)...
cd /d "%API_DIR%"
if errorlevel 1 (
    echo [ERROR] apps\api no encontrado
    exit /b 1
)

set "BACKEND_RUNNER=uvicorn"

if exist pyproject.toml (
    where uv >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Se encontro apps\api\pyproject.toml pero 'uv' no esta instalado.
        echo [ERROR] Instala uv desde https://docs.astral.sh/uv/ y vuelve a correr este script.
        exit /b 1
    )

    if not exist venv (
        echo [INFO] Creando entorno virtual de Python con uv...
        uv venv venv
        if errorlevel 1 (
            echo [ERROR] No se pudo crear el venv con uv
            exit /b 1
        )
    )

    call venv\Scripts\activate.bat
    echo [INFO] Sincronizando dependencias del backend con uv...
    uv sync --active
    if errorlevel 1 (
        echo [ERROR] La sincronizacion de dependencias del backend fallo.
        call venv\Scripts\deactivate.bat
        exit /b 1
    )
    set "BACKEND_RUNNER=uv run uvicorn"
) else (
    if not exist requirements.txt (
        echo [ERROR] No se encontro ni apps\api\pyproject.toml ni apps\api\requirements.txt
        exit /b 1
    )

    if not exist venv (
        echo [INFO] Creando entorno virtual de Python...
        %PY_CMD% -m venv venv
        if errorlevel 1 (
            echo [ERROR] No se pudo crear el venv
            exit /b 1
        )
    )

    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip --quiet

    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [WARN] Conflicto de dependencias detectado - reintentando con --no-cache-dir...
        pip install -r requirements.txt --no-cache-dir
        if errorlevel 1 (
            echo [ERROR] La instalacion de dependencias del backend fallo.
            call venv\Scripts\deactivate.bat
            exit /b 1
        )
    )
)

REM Auto-deteccion del modulo de entrada de FastAPI
set "API_MODULE="
if defined APP_MODULE_OVERRIDE (
    set "API_MODULE=%APP_MODULE_OVERRIDE%"
) else if exist server.py (
    set "API_MODULE=server:app"
) else if exist main.py (
    set "API_MODULE=main:app"
) else if exist app\main.py (
    set "API_MODULE=app.main:app"
)

if not defined API_MODULE (
    echo [ERROR] No se pudo detectar el entry point de FastAPI en apps\api.
    echo [ERROR] Edita APP_MODULE_OVERRIDE al inicio de este script ^(ej: app.main:app^).
    call venv\Scripts\deactivate.bat
    exit /b 1
)
echo [INFO] Entry point detectado: %API_MODULE%

start "xambas API" cmd /k "call venv\Scripts\activate.bat && %BACKEND_RUNNER% %API_MODULE% --host 0.0.0.0 --port %BACKEND_PORT% --reload"

cd /d "%ROOT_DIR%"

REM ---------- 7. Servir los builds de client y provider ----------
echo [INFO] Sirviendo build de 'client' en el puerto %CLIENT_PREVIEW_PORT%...
start "xambas Client" cmd /k "cd /d "%CLIENT_DIR%" && call %PKGMGR% vite preview --port %CLIENT_PREVIEW_PORT% --host"

echo [INFO] Sirviendo build de 'provider' en el puerto %PROVIDER_PREVIEW_PORT%...
start "xambas Provider" cmd /k "cd /d "%PROVIDER_DIR%" && call %PKGMGR% vite preview --port %PROVIDER_PREVIEW_PORT% --host"

echo [INFO] Sirviendo build de 'admin' en el puerto %ADMIN_PREVIEW_PORT%...
start "xambas Admin" cmd /k "cd /d "%ADMIN_DIR%" && call %PKGMGR% vite preview --port %ADMIN_PREVIEW_PORT% --host"

echo [INFO] Sirviendo build de 'web' en el puerto %WEB_PREVIEW_PORT%...
start "xambas Web" cmd /k "cd /d "%WEB_DIR%" && call %PKGMGR% vite preview --port %WEB_PREVIEW_PORT% --host"

echo.
echo ========================================
echo   Deploy completo!
echo ========================================
echo.
echo Backend (FastAPI):  http://localhost:%BACKEND_PORT%
echo Client:              http://localhost:%CLIENT_PREVIEW_PORT%
echo Provider:            http://localhost:%PROVIDER_PREVIEW_PORT%
echo Admin:               http://localhost:%ADMIN_PREVIEW_PORT%
echo Web:                 http://localhost:%WEB_PREVIEW_PORT%
echo.
echo Cada servicio corre en su propia ventana. Cierrala para detenerlo.
echo.

endlocal

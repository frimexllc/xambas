#!/usr/bin/env bash
# Preview-environment entrypoint shim.
# The platform supervisor runs `yarn start` from /app/frontend on port 3000.
# We serve the chosen monorepo Vite app (default: client) on that port.
set -e
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

APP="${PREVIEW_APP:-client}"
cd "/app/apps/${APP}"

exec yarn vite --host 0.0.0.0 --port 3000 --strictPort

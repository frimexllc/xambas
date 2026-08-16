"""Preview-environment entrypoint shim.

The platform supervisor launches `uvicorn server:app` from `/app/backend`.
The real FastAPI application lives in the monorepo at `apps/api`. This shim
only wires the import path so the monorepo code runs unchanged.
"""

import sys
from pathlib import Path

API_ROOT = Path("/app/apps/api")
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.main import app  # noqa: E402,F401

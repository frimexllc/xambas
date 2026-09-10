"""Fixtures compartidas para la suite de integración de la API de Xambas.

Estas pruebas corren contra una instancia **en ejecución** de la API (no montan
la app en proceso). La URL base se resuelve, en orden de prioridad:

1. ``XAMBAS_API_URL`` (usada por el workflow de CI, apunta a ``127.0.0.1:8000``).
2. ``REACT_APP_BACKEND_URL`` (compatibilidad con el entorno de preview Emergent).
3. ``http://localhost:8000`` (desarrollo local con ``deploy.bat`` / uvicorn).

El catálogo de categorías se siembra solo al arrancar la API
(``ensure_launch_categories``), así que los IDs se resuelven en tiempo de
ejecución: una base de datos limpia genera IDs de Mongo nuevos en cada corrida.
"""
from __future__ import annotations

import io
import time

import pytest
import requests

from tests.helpers import BASE_URL, LIMPIEZA_BASICA, REQUEST_TIMEOUT, run_external_enabled


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "external: la prueba llama a un servicio externo real (Groq); "
        "se salta salvo XAMBAS_RUN_EXTERNAL_TESTS=1",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if run_external_enabled():
        return
    skip_external = pytest.mark.skip(
        reason="requiere XAMBAS_RUN_EXTERNAL_TESTS=1 (llamada real a Groq)"
    )
    for item in items:
        if "external" in item.keywords:
            item.add_marker(skip_external)


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def _api_is_up(base_url: str) -> None:
    """Falla rápido y con un mensaje claro si la API no está corriendo."""
    last_error: Exception | None = None
    for _ in range(30):
        try:
            r = requests.get(f"{base_url}/health", timeout=(5, 10))
            if r.status_code == 200:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(1)
    pytest.fail(
        f"La API no respondió en {base_url}/health. "
        f"Levántala antes de correr las pruebas (uvicorn app.main:app). Último error: {last_error}"
    )


@pytest.fixture(scope="module")
def api() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def categories(base_url: str) -> list[dict]:
    r = requests.get(f"{base_url}/api/matching/categories", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    body = r.json()
    items = body.get("items") or body.get("categories") or []
    assert items, "el catálogo de categorías está vacío; ¿arrancó la API y sembró seeds?"
    return items


@pytest.fixture(scope="session")
def any_category_id(categories: list[dict]) -> str:
    return categories[0]["id"]


@pytest.fixture(scope="session")
def limpieza_basica_category_id(categories: list[dict]) -> str:
    for category in categories:
        if category["name"] == LIMPIEZA_BASICA:
            return category["id"]
    pytest.fail(
        f"No se encontró la subcategoría {LIMPIEZA_BASICA!r} en el catálogo sembrado. "
        f"Nombres disponibles: {sorted(c['name'] for c in categories)}"
    )


@pytest.fixture(scope="session")
def sample_image_bytes() -> bytes:
    """JPEG mínimo válido generado en memoria (evita depender de archivos del entorno)."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (48, 48), (200, 180, 160)).save(buffer, format="JPEG")
    return buffer.getvalue()

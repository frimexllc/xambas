"""Pruebas de integración del módulo ai_quote (Xambas).

Los endpoints `/api/ai-quote/*` (salvo `/status` y `/files/*`) exigen
``Authorization: Bearer <token>`` y el cliente sale del token.

Las pruebas de camino feliz llaman a Groq de verdad (red + costo): marcadas
``external``, se saltan salvo ``XAMBAS_RUN_EXTERNAL_TESTS=1``.
"""
from __future__ import annotations

import time

import pytest
import requests

from tests.helpers import BASE_URL, authed_client

REQUEST_TIMEOUT = (10, 120)


@pytest.fixture(scope="module")
def client_ctx():
    return authed_client(BASE_URL)


def _post_estimate(session, sample_image_bytes, *, data=None):
    files = [("files", ("kitchen.jpg", sample_image_bytes, "image/jpeg"))]
    # requests.Session fija Content-Type: application/json; para multipart hay
    # que quitarlo y dejar que requests ponga el boundary.
    headers = {k: v for k, v in session.headers.items() if k.lower() != "content-type"}
    return requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        data=data or {},
        files=files,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )


# --- status (público) ---------------------------------------------------
def test_status_ready() -> None:
    r = requests.get(f"{BASE_URL}/api/ai-quote/status", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["module"] == "ai_quote"
    assert data["status"] in {"ready", "missing_api_key"}
    assert data["provider"] == "groq"
    assert data["model"] == "qwen/qwen3.6-27b"


# --- auth --------------------------------------------------------------
def test_estimate_requires_auth(sample_image_bytes: bytes) -> None:
    files = [("files", ("kitchen.jpg", sample_image_bytes, "image/jpeg"))]
    r = requests.post(f"{BASE_URL}/api/ai-quote/estimate", files=files, timeout=REQUEST_TIMEOUT)
    assert r.status_code == 401


def test_list_estimates_requires_auth() -> None:
    assert requests.get(f"{BASE_URL}/api/ai-quote/estimates").status_code == 401


# --- validaciones (con auth, no llaman a Groq) ------------------------
def test_estimate_requires_files(client_ctx) -> None:
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        headers={"Authorization": f"Bearer {client_ctx.token}"},
        data={},
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code in (400, 422), f"esperaba 400/422, recibí {r.status_code}: {r.text}"


def test_estimate_rejects_non_image(client_ctx) -> None:
    files = [("files", ("note.txt", b"hello world", "text/plain"))]
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        headers={"Authorization": f"Bearer {client_ctx.token}"},
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 415, f"recibí {r.status_code}: {r.text}"


def test_get_estimate_not_found(client_ctx) -> None:
    r = client_ctx.session.get(
        f"{BASE_URL}/api/ai-quote/estimates/0123456789abcdef01234567", timeout=REQUEST_TIMEOUT
    )
    assert r.status_code == 404


# --- camino feliz (Groq real) ----------------------------------------
# El fixture solo se materializa si una prueba marcada ``external`` lo pide.
@pytest.fixture(scope="module")
def created_quote(client_ctx, any_category_id: str, sample_image_bytes: bytes) -> dict:
    last_error = None
    for _ in range(2):
        r = _post_estimate(
            client_ctx.session,
            sample_image_bytes,
            data={"notes": "Cocina, limpieza profunda", "category_id": any_category_id},
        )
        if r.status_code == 200:
            return r.json()["quote"]
        last_error = f"{r.status_code} {r.text}"
        time.sleep(1)
    pytest.fail(f"Groq estimate falló dos veces: {last_error}")


@pytest.mark.external
def test_estimate_happy_path(created_quote: dict) -> None:
    q = created_quote
    assert isinstance(q["id"], str) and q["id"]
    assert isinstance(q["scope"], list) and len(q["scope"]) >= 1
    assert q["price_min"] <= q["price_max"]
    assert q["currency"] == "MXN"
    assert 0.0 <= q["confidence"] <= 1.0
    assert len(q["suggested_title"]) >= 4
    assert len(q["suggested_description"]) >= 10
    img = q["images"][0]
    assert img["url"].startswith("/api/ai-quote/files/")
    assert img["content_type"] == "image/jpeg"


@pytest.mark.external
def test_list_estimates_by_client(client_ctx, created_quote: dict) -> None:
    r = client_ctx.session.get(f"{BASE_URL}/api/ai-quote/estimates", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["module"] == "ai_quote"
    assert created_quote["id"] in [item["id"] for item in body["items"]]
    assert body["total"] == len(body["items"])


@pytest.mark.external
def test_get_estimate_by_id(client_ctx, created_quote: dict) -> None:
    r = client_ctx.session.get(
        f"{BASE_URL}/api/ai-quote/estimates/{created_quote['id']}", timeout=REQUEST_TIMEOUT
    )
    assert r.status_code == 200, r.text
    assert r.json()["quote"]["id"] == created_quote["id"]


@pytest.mark.external
def test_other_client_cannot_read_estimate(created_quote: dict) -> None:
    intruder = authed_client(BASE_URL)
    r = intruder.session.get(
        f"{BASE_URL}/api/ai-quote/estimates/{created_quote['id']}", timeout=REQUEST_TIMEOUT
    )
    assert r.status_code == 403


@pytest.mark.external
def test_get_file_serves_image(created_quote: dict) -> None:
    # /files/* no lleva auth (URL-capacidad): las <img> del navegador no mandan header.
    r = requests.get(f"{BASE_URL}{created_quote['images'][0]['url']}", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 100


# --- regresión ligera --------------------------------------------------
def test_matching_service_requests_still_ok(client_ctx) -> None:
    r = client_ctx.session.get(f"{BASE_URL}/api/matching/service-requests", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body or "service_requests" in body or "requests" in body


def test_matching_service_requests_requires_auth() -> None:
    assert requests.get(f"{BASE_URL}/api/matching/service-requests").status_code == 401

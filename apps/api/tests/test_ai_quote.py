"""Pruebas de integración del módulo ai_quote (Xambas).

Las pruebas de camino feliz llaman a Groq de verdad (red + costo), así que
están marcadas ``external`` y se saltan salvo ``XAMBAS_RUN_EXTERNAL_TESTS=1``.
El resto (status, validaciones) corre siempre y no necesita GROQ_API_KEY.
"""
from __future__ import annotations

import time

import pytest
import requests

from tests.helpers import BASE_URL, bootstrap_client, verify_otp_for

REQUEST_TIMEOUT = (10, 120)


@pytest.fixture(scope="module")
def client_id() -> str:
    user = bootstrap_client(BASE_URL)
    verify_otp_for(BASE_URL, user["id"])
    return user["id"]


# --- status --------------------------------------------------------------
def test_status_ready() -> None:
    r = requests.get(f"{BASE_URL}/api/ai-quote/status", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["module"] == "ai_quote"
    # "ready" con GROQ_API_KEY configurada; "missing_api_key" sin ella (CI por defecto).
    assert data["status"] in {"ready", "missing_api_key"}
    assert data["provider"] == "groq"
    assert data["model"] == "qwen/qwen3.6-27b"


# --- validaciones (no llaman a Groq) -----------------------------------
def test_estimate_requires_files(client_id: str) -> None:
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        data={"client_id": client_id},
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code in (400, 422), f"esperaba 400/422, recibí {r.status_code}: {r.text}"


def test_estimate_rejects_non_image(client_id: str) -> None:
    files = [("files", ("note.txt", b"hello world", "text/plain"))]
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        data={"client_id": client_id},
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 415, f"recibí {r.status_code}: {r.text}"


def test_estimate_unknown_client(sample_image_bytes: bytes) -> None:
    fake_id = "0123456789abcdef01234567"
    files = [("files", ("kitchen.jpg", sample_image_bytes, "image/jpeg"))]
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        data={"client_id": fake_id},
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 404, f"recibí {r.status_code}: {r.text}"


def test_get_estimate_not_found() -> None:
    r = requests.get(
        f"{BASE_URL}/api/ai-quote/estimates/0123456789abcdef01234567",
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 404


# --- camino feliz (Groq real) ----------------------------------------
# El fixture solo se materializa si una prueba marcada ``external`` lo pide,
# y esas se saltan salvo XAMBAS_RUN_EXTERNAL_TESTS=1.
@pytest.fixture(scope="module")
def created_quote(client_id: str, any_category_id: str, sample_image_bytes: bytes) -> dict:
    files = [("files", ("kitchen.jpg", sample_image_bytes, "image/jpeg"))]
    data = {
        "client_id": client_id,
        "notes": "Cocina, servicio de limpieza profunda",
        "category_id": any_category_id,
    }
    last_error = None
    for _ in range(2):
        r = requests.post(
            f"{BASE_URL}/api/ai-quote/estimate", data=data, files=files, timeout=(10, 120)
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
    assert isinstance(q["suggested_title"], str) and len(q["suggested_title"]) >= 4
    assert isinstance(q["suggested_description"], str) and len(q["suggested_description"]) >= 10
    assert isinstance(q["images"], list) and len(q["images"]) == 1
    img = q["images"][0]
    assert img["url"].startswith("/api/ai-quote/files/")
    assert img["content_type"] == "image/jpeg"


@pytest.mark.external
def test_list_estimates_by_client(client_id: str, created_quote: dict) -> None:
    r = requests.get(
        f"{BASE_URL}/api/ai-quote/estimates",
        params={"client_id": client_id},
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["module"] == "ai_quote"
    ids = [item["id"] for item in body["items"]]
    assert created_quote["id"] in ids
    assert body["total"] == len(body["items"])


@pytest.mark.external
def test_get_estimate_by_id(created_quote: dict) -> None:
    r = requests.get(
        f"{BASE_URL}/api/ai-quote/estimates/{created_quote['id']}", timeout=REQUEST_TIMEOUT
    )
    assert r.status_code == 200, r.text
    assert r.json()["quote"]["id"] == created_quote["id"]


@pytest.mark.external
def test_get_file_serves_image(created_quote: dict) -> None:
    url_path = created_quote["images"][0]["url"]
    r = requests.get(f"{BASE_URL}{url_path}", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 100


# --- regresión ligera --------------------------------------------------
def test_matching_service_requests_still_ok() -> None:
    r = requests.get(f"{BASE_URL}/api/matching/service-requests", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body or "service_requests" in body or "requests" in body

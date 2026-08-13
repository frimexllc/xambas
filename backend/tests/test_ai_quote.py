"""Backend tests for the ai_quote module (Xambas).

Covers:
  * GET /api/ai-quote/status
  * POST /api/ai-quote/estimate (happy path with real Groq call)
  * Validation errors: no files, unsupported type, unknown client
  * GET /api/ai-quote/estimates?client_id=
  * GET /api/ai-quote/estimates/{id}
  * GET /api/ai-quote/files/{path}
  * Light regression on /api/matching/service-requests (recurring/matching)
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import pytest
import requests

BASE_URL = "https://6a5a4228-856c-435a-9735-832a8c1fd2f3.preview.emergentagent.com"
IMAGE_PATH = Path("/tmp/kitchen.jpg")

REQUEST_TIMEOUT = (10, 90)  # (connect, read) - Groq vision can take ~5-10s


# --- helpers ---------------------------------------------------------------


def _register_client() -> str:
    unique = uuid.uuid4().hex[:8]
    email = f"TEST_aiq_{unique}@example.com"
    phone = f"+5255{int(time.time()) % 100000000:08d}"
    r = requests.post(
        f"{BASE_URL}/api/identity/bootstrap",
        json={"email": email, "phone": phone, "role": "client"},
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code in (200, 201), f"bootstrap failed: {r.status_code} {r.text}"
    user_id = r.json()["user"]["id"]

    r = requests.post(
        f"{BASE_URL}/api/identity/otp/request",
        json={"user_id": user_id, "purpose": "registration", "channel": "sms"},
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    challenge_id = body["challenge"]["id"] if "challenge" in body else body.get("challenge_id")
    code = body.get("debug_code") or body.get("challenge", {}).get("debug_code")
    assert code, f"no debug_code in {body}"

    r = requests.post(
        f"{BASE_URL}/api/identity/otp/verify",
        json={
            "user_id": user_id,
            "challenge_id": challenge_id,
            "code": code,
            "device_name": "pytest",
        },
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    return user_id


@pytest.fixture(scope="module")
def client_id() -> str:
    return _register_client()


@pytest.fixture(scope="module")
def category_id() -> str | None:
    r = requests.get(f"{BASE_URL}/api/matching/categories", timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        return None
    items = r.json().get("items") or r.json().get("categories") or []
    return items[0]["id"] if items else None


# --- status ---------------------------------------------------------------


def test_status_ready() -> None:
    r = requests.get(f"{BASE_URL}/api/ai-quote/status", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["module"] == "ai_quote"
    assert data["status"] == "ready"
    assert data["provider"] == "groq"
    assert data["model"] == "qwen/qwen3.6-27b"


# --- validations ----------------------------------------------------------


def test_estimate_requires_files(client_id: str) -> None:
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        data={"client_id": client_id},
        timeout=REQUEST_TIMEOUT,
    )
    # multipart missing 'files' -> FastAPI returns 422 (validation) since files is required
    assert r.status_code in (400, 422), f"expected 400/422, got {r.status_code}: {r.text}"


def test_estimate_rejects_non_image(client_id: str) -> None:
    files = [("files", ("note.txt", b"hello world", "text/plain"))]
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        data={"client_id": client_id},
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 415, f"got {r.status_code}: {r.text}"


def test_estimate_unknown_client() -> None:
    # valid ObjectId shape but not existing
    fake_id = "0123456789abcdef01234567"
    files = [("files", ("kitchen.jpg", IMAGE_PATH.read_bytes(), "image/jpeg"))]
    r = requests.post(
        f"{BASE_URL}/api/ai-quote/estimate",
        data={"client_id": fake_id},
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 404, f"got {r.status_code}: {r.text}"


# --- happy path (real Groq) -----------------------------------------------


@pytest.fixture(scope="module")
def created_quote(client_id: str, category_id: str | None) -> dict:
    files = [("files", ("kitchen.jpg", IMAGE_PATH.read_bytes(), "image/jpeg"))]
    data = {"client_id": client_id, "notes": "Cocina, servicio de limpieza profunda"}
    if category_id:
        data["category_id"] = category_id

    last_error = None
    for attempt in range(2):  # one retry allowed per instructions
        r = requests.post(
            f"{BASE_URL}/api/ai-quote/estimate",
            data=data,
            files=files,
            timeout=(10, 120),
        )
        if r.status_code == 200:
            return r.json()["quote"]
        last_error = f"{r.status_code} {r.text}"
        time.sleep(1)
    pytest.fail(f"Groq estimate failed twice: {last_error}")


def test_estimate_happy_path(created_quote: dict) -> None:
    q = created_quote
    assert isinstance(q["id"], str) and q["id"]
    assert isinstance(q["scope"], list) and len(q["scope"]) >= 1
    assert isinstance(q["price_min"], (int, float))
    assert isinstance(q["price_max"], (int, float))
    assert q["price_min"] <= q["price_max"]
    assert q["currency"] == "MXN"
    assert 0.0 <= q["confidence"] <= 1.0
    assert isinstance(q["suggested_title"], str) and len(q["suggested_title"]) >= 4
    assert isinstance(q["suggested_description"], str) and len(q["suggested_description"]) >= 10
    assert isinstance(q["images"], list) and len(q["images"]) == 1
    img = q["images"][0]
    assert img["url"].startswith("/api/ai-quote/files/")
    assert img["content_type"] == "image/jpeg"


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


def test_get_estimate_by_id(created_quote: dict) -> None:
    r = requests.get(
        f"{BASE_URL}/api/ai-quote/estimates/{created_quote['id']}",
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["quote"]["id"] == created_quote["id"]


def test_get_estimate_not_found() -> None:
    r = requests.get(
        f"{BASE_URL}/api/ai-quote/estimates/0123456789abcdef01234567",
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 404


def test_get_file_serves_image(created_quote: dict) -> None:
    url_path = created_quote["images"][0]["url"]
    r = requests.get(f"{BASE_URL}{url_path}", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert ct.startswith("image/"), f"unexpected content-type: {ct}"
    assert len(r.content) > 100


# --- light regression -----------------------------------------------------


def test_matching_service_requests_still_ok() -> None:
    r = requests.get(f"{BASE_URL}/api/matching/service-requests", timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body or "service_requests" in body or "requests" in body

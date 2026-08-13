"""Backend tests for recurring subscriptions module (Xambas)."""
import os
import uuid
from datetime import date, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://6a5a4228-856c-435a-9735-832a8c1fd2f3.preview.emergentagent.com").rstrip("/")
CATEGORY_ID_LIMPIEZA_BASICA = "6a7d4c75b514b1dcdaeafdd8"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def client_user(api):
    """Bootstrap a new client user."""
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"TEST_client_{suffix}@example.com",
        "phone": f"+52155512{suffix[:5]}",
        "role": "client",
        "locale": "es-MX",
    }
    r = api.post(f"{BASE_URL}/api/identity/bootstrap", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["user"]


@pytest.fixture(scope="module")
def provider_user(api):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"TEST_prov_{suffix}@example.com",
        "phone": f"+52155513{suffix[:5]}",
        "role": "provider",
        "locale": "es-MX",
        "provider_profile": {
            "business_name": "TEST Provider",
            "categories": [CATEGORY_ID_LIMPIEZA_BASICA],
            "coverage_zones": ["Roma Norte"],
        },
    }
    r = api.post(f"{BASE_URL}/api/identity/bootstrap", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["user"]


def _create_subscription(api, client_id, frequency="weekly", start_date=None):
    payload = {
        "client_id": client_id,
        "category_id": CATEGORY_ID_LIMPIEZA_BASICA,
        "title": "Limpieza semanal test",
        "description": "Servicio de limpieza recurrente para pruebas automatizadas.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": "Roma Norte",
        "frequency": frequency,
        "budget_amount": 500.0,
        "preferred_time": "morning",
        "attributes": {},
    }
    if start_date:
        payload["start_date"] = start_date
    r = api.post(f"{BASE_URL}/api/recurring/subscriptions", json=payload)
    return r


# ----------------- STATUS -----------------
def test_status(api):
    r = api.get(f"{BASE_URL}/api/recurring/status")
    assert r.status_code == 200
    d = r.json()
    assert d["module"] == "recurring"
    assert d["status"] == "ready"
    assert set(d["supported_frequencies"]) == {"weekly", "biweekly", "monthly"}


# ----------------- CREATE -----------------
def test_create_subscription_defaults_to_today(api, client_user):
    r = _create_subscription(api, client_user["id"])
    assert r.status_code == 200, r.text
    sub = r.json()["subscription"]
    assert sub["status"] == "active"
    assert sub["start_date"] == date.today().isoformat()
    assert sub["next_run_date"] == sub["start_date"]
    assert sub["occurrences_count"] == 0
    assert sub["category_name"] == "Limpieza Basica"


def test_create_subscription_with_start_date(api, client_user):
    future = (date.today() + timedelta(days=3)).isoformat()
    r = _create_subscription(api, client_user["id"], start_date=future)
    assert r.status_code == 200
    sub = r.json()["subscription"]
    assert sub["start_date"] == future
    assert sub["next_run_date"] == future


def test_create_subscription_provider_rejected(api, provider_user):
    r = _create_subscription(api, provider_user["id"])
    assert r.status_code == 422


def test_create_subscription_invalid_client(api):
    r = _create_subscription(api, "000000000000000000000000")
    assert r.status_code == 404


def test_create_subscription_invalid_category(api, client_user):
    payload = {
        "client_id": client_user["id"],
        "category_id": "000000000000000000000000",
        "title": "Test invalido",
        "description": "Descripcion suficientemente larga para pasar la validacion.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": "Roma Norte",
        "frequency": "weekly",
    }
    r = api.post(f"{BASE_URL}/api/recurring/subscriptions", json=payload)
    assert r.status_code == 404


# ----------------- LIST / GET -----------------
def test_list_subscriptions_filtered_by_client(api, client_user):
    r = api.get(f"{BASE_URL}/api/recurring/subscriptions", params={"client_id": client_user["id"]})
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2
    for item in d["items"]:
        assert item["client_id"] == client_user["id"]


# ----------------- GENERATE -----------------
def test_generate_occurrence_weekly(api, client_user):
    start = date.today().isoformat()
    r = _create_subscription(api, client_user["id"], frequency="weekly", start_date=start)
    sub_id = r.json()["subscription"]["id"]

    gen = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200, gen.text
    data = gen.json()
    assert data["occurrence"]["request_id"]
    assert data["occurrence"]["scheduled_date"] == start
    assert data["subscription"]["occurrences_count"] == 1
    expected_next = (date.today() + timedelta(days=7)).isoformat()
    assert data["subscription"]["next_run_date"] == expected_next

    # occurrences endpoint
    occ = api.get(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/occurrences")
    assert occ.status_code == 200
    body = occ.json()
    assert body["total"] == 1
    assert body["items"][0]["request_id"] == data["occurrence"]["request_id"]

    # verify the service_request exists via matching module
    req_id = data["occurrence"]["request_id"]
    sr = api.get(f"{BASE_URL}/api/matching/service-requests/{req_id}")
    assert sr.status_code == 200, sr.text


def test_generate_occurrence_biweekly(api, client_user):
    start = date.today().isoformat()
    r = _create_subscription(api, client_user["id"], frequency="biweekly", start_date=start)
    sub_id = r.json()["subscription"]["id"]
    gen = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200
    expected = (date.today() + timedelta(days=14)).isoformat()
    assert gen.json()["subscription"]["next_run_date"] == expected


def test_generate_occurrence_monthly(api, client_user):
    start = date.today().isoformat()
    r = _create_subscription(api, client_user["id"], frequency="monthly", start_date=start)
    sub_id = r.json()["subscription"]["id"]
    gen = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200
    next_run = gen.json()["subscription"]["next_run_date"]
    # ensure it's roughly a month later - different from start
    assert next_run != start
    assert next_run > start


# ----------------- PAUSE / RESUME / CANCEL -----------------
def test_pause_resume_cancel_flow(api, client_user):
    r = _create_subscription(api, client_user["id"])
    sub_id = r.json()["subscription"]["id"]

    # pause
    p = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/pause")
    assert p.status_code == 200
    assert p.json()["subscription"]["status"] == "paused"

    # generate while paused -> 409
    g = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert g.status_code == 409

    # resume
    res = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/resume")
    assert res.status_code == 200
    assert res.json()["subscription"]["status"] == "active"

    # generate now works
    g2 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert g2.status_code == 200

    # cancel
    c = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/cancel")
    assert c.status_code == 200
    assert c.json()["subscription"]["status"] == "cancelled"

    # pause/resume after cancel -> 409
    p2 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/pause")
    assert p2.status_code == 409
    r2 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/resume")
    assert r2.status_code == 409
    # generate after cancel -> 409 (not active)
    g3 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert g3.status_code == 409


# ----------------- REGRESSION: matching service-requests still works -----------------
def test_regression_create_service_request(api, client_user):
    payload = {
        "client_id": client_user["id"],
        "category_id": CATEGORY_ID_LIMPIEZA_BASICA,
        "title": "Solicitud regresion",
        "description": "Prueba de regresion del flujo de solicitudes.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": "Roma Norte",
        "budget_amount": 400.0,
    }
    r = api.post(f"{BASE_URL}/api/matching/service-requests", json=payload)
    assert r.status_code == 200, r.text
    assert "request" in r.json()


# ----------------- 404 subscription -----------------
def test_subscription_not_found(api):
    r = api.get(f"{BASE_URL}/api/recurring/subscriptions/000000000000000000000000")
    assert r.status_code == 404

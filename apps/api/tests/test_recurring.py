"""Pruebas de integración del módulo de servicios recurrentes (Xambas)."""
from datetime import date, timedelta

import pytest

from tests.helpers import BASE_URL, bootstrap_client, bootstrap_provider


@pytest.fixture(scope="module")
def client_user() -> dict:
    return bootstrap_client(BASE_URL)


@pytest.fixture(scope="module")
def provider_user(limpieza_basica_category_id: str) -> dict:
    return bootstrap_provider(BASE_URL, limpieza_basica_category_id, ["Roma Norte"])


def _create_subscription(api, client_id, category_id, frequency="weekly", start_date=None):
    payload = {
        "client_id": client_id,
        "category_id": category_id,
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
    return api.post(f"{BASE_URL}/api/recurring/subscriptions", json=payload)


# ----------------- STATUS -----------------
def test_status(api):
    r = api.get(f"{BASE_URL}/api/recurring/status")
    assert r.status_code == 200
    d = r.json()
    assert d["module"] == "recurring"
    assert d["status"] == "ready"
    assert set(d["supported_frequencies"]) == {"weekly", "biweekly", "monthly"}


# ----------------- CREATE -----------------
def test_create_subscription_defaults_to_today(api, client_user, limpieza_basica_category_id):
    r = _create_subscription(api, client_user["id"], limpieza_basica_category_id)
    assert r.status_code == 200, r.text
    sub = r.json()["subscription"]
    assert sub["status"] == "active"
    # El servidor usa su propio reloj (UTC); toleramos el desfase de zona horaria
    # entre la máquina de pruebas y la API.
    today = date.today()
    assert sub["start_date"] in {
        (today - timedelta(days=1)).isoformat(),
        today.isoformat(),
        (today + timedelta(days=1)).isoformat(),
    }
    assert sub["next_run_date"] == sub["start_date"]
    assert sub["occurrences_count"] == 0
    assert sub["category_name"] == "Limpieza Basica"


def test_create_subscription_with_start_date(api, client_user, limpieza_basica_category_id):
    future = (date.today() + timedelta(days=3)).isoformat()
    r = _create_subscription(api, client_user["id"], limpieza_basica_category_id, start_date=future)
    assert r.status_code == 200
    sub = r.json()["subscription"]
    assert sub["start_date"] == future
    assert sub["next_run_date"] == future


def test_create_subscription_provider_rejected(api, provider_user, limpieza_basica_category_id):
    r = _create_subscription(api, provider_user["id"], limpieza_basica_category_id)
    assert r.status_code == 422


def test_create_subscription_invalid_client(api, limpieza_basica_category_id):
    r = _create_subscription(api, "000000000000000000000000", limpieza_basica_category_id)
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
def test_list_subscriptions_filtered_by_client(api, client_user, limpieza_basica_category_id):
    # asegura al menos 2 suscripciones de este cliente
    _create_subscription(api, client_user["id"], limpieza_basica_category_id)
    _create_subscription(api, client_user["id"], limpieza_basica_category_id)
    r = api.get(f"{BASE_URL}/api/recurring/subscriptions", params={"client_id": client_user["id"]})
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2
    for item in d["items"]:
        assert item["client_id"] == client_user["id"]


# ----------------- GENERATE -----------------
def test_generate_occurrence_weekly(api, client_user, limpieza_basica_category_id):
    start = date.today().isoformat()
    r = _create_subscription(api, client_user["id"], limpieza_basica_category_id, frequency="weekly", start_date=start)
    sub_id = r.json()["subscription"]["id"]

    gen = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200, gen.text
    data = gen.json()
    assert data["occurrence"]["request_id"]
    assert data["occurrence"]["scheduled_date"] == start
    assert data["subscription"]["occurrences_count"] == 1
    expected_next = (date.today() + timedelta(days=7)).isoformat()
    assert data["subscription"]["next_run_date"] == expected_next

    occ = api.get(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/occurrences")
    assert occ.status_code == 200
    body = occ.json()
    assert body["total"] == 1
    assert body["items"][0]["request_id"] == data["occurrence"]["request_id"]

    req_id = data["occurrence"]["request_id"]
    sr = api.get(f"{BASE_URL}/api/matching/service-requests/{req_id}")
    assert sr.status_code == 200, sr.text


def test_generate_occurrence_biweekly(api, client_user, limpieza_basica_category_id):
    start = date.today().isoformat()
    r = _create_subscription(api, client_user["id"], limpieza_basica_category_id, frequency="biweekly", start_date=start)
    sub_id = r.json()["subscription"]["id"]
    gen = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200
    expected = (date.today() + timedelta(days=14)).isoformat()
    assert gen.json()["subscription"]["next_run_date"] == expected


def test_generate_occurrence_monthly(api, client_user, limpieza_basica_category_id):
    start = date.today().isoformat()
    r = _create_subscription(api, client_user["id"], limpieza_basica_category_id, frequency="monthly", start_date=start)
    sub_id = r.json()["subscription"]["id"]
    gen = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200
    next_run = gen.json()["subscription"]["next_run_date"]
    assert next_run != start
    assert next_run > start


# ----------------- PAUSE / RESUME / CANCEL -----------------
def test_pause_resume_cancel_flow(api, client_user, limpieza_basica_category_id):
    r = _create_subscription(api, client_user["id"], limpieza_basica_category_id)
    sub_id = r.json()["subscription"]["id"]

    p = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/pause")
    assert p.status_code == 200
    assert p.json()["subscription"]["status"] == "paused"

    g = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert g.status_code == 409

    res = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/resume")
    assert res.status_code == 200
    assert res.json()["subscription"]["status"] == "active"

    g2 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert g2.status_code == 200

    c = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/cancel")
    assert c.status_code == 200
    assert c.json()["subscription"]["status"] == "cancelled"

    p2 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/pause")
    assert p2.status_code == 409
    r2 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/resume")
    assert r2.status_code == 409
    g3 = api.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert g3.status_code == 409


# ----------------- REGRESIÓN: matching sigue funcionando -----------------
def test_regression_create_service_request(api, client_user, limpieza_basica_category_id):
    payload = {
        "client_id": client_user["id"],
        "category_id": limpieza_basica_category_id,
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


# ----------------- 404 -----------------
def test_subscription_not_found(api):
    r = api.get(f"{BASE_URL}/api/recurring/subscriptions/000000000000000000000000")
    assert r.status_code == 404

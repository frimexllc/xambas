"""Pruebas de integración del módulo de servicios recurrentes (Xambas).

Todos los endpoints `/api/recurring/*` (salvo `/status`) exigen
``Authorization: Bearer <token>`` y el cliente se toma del token, no del body.
"""
from datetime import date, timedelta

import pytest
import requests

from tests.helpers import BASE_URL, authed_client, authed_provider


@pytest.fixture(scope="module")
def client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def other_client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def provider_ctx(limpieza_basica_category_id: str):
    return authed_provider(BASE_URL, limpieza_basica_category_id, ["Roma Norte"])


def _payload(category_id, frequency="weekly", start_date=None):
    body = {
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
        body["start_date"] = start_date
    return body


def _create(session, category_id, **kwargs):
    return session.post(f"{BASE_URL}/api/recurring/subscriptions", json=_payload(category_id, **kwargs))


# ----------------- STATUS (público) -----------------
def test_status():
    r = requests.get(f"{BASE_URL}/api/recurring/status")
    assert r.status_code == 200
    d = r.json()
    assert d["module"] == "recurring"
    assert d["status"] == "ready"
    assert set(d["supported_frequencies"]) == {"weekly", "biweekly", "monthly"}


# ----------------- AUTH -----------------
def test_create_requires_auth(limpieza_basica_category_id):
    r = requests.post(
        f"{BASE_URL}/api/recurring/subscriptions", json=_payload(limpieza_basica_category_id)
    )
    assert r.status_code == 401


def test_list_requires_auth():
    assert requests.get(f"{BASE_URL}/api/recurring/subscriptions").status_code == 401


def test_bogus_token_rejected(limpieza_basica_category_id):
    r = requests.get(
        f"{BASE_URL}/api/recurring/subscriptions",
        headers={"Authorization": "Bearer no-es-un-token-real"},
    )
    assert r.status_code == 401


# ----------------- CREATE -----------------
def test_create_subscription_defaults_to_today(client_ctx, limpieza_basica_category_id):
    r = _create(client_ctx.session, limpieza_basica_category_id)
    assert r.status_code == 200, r.text
    sub = r.json()["subscription"]
    assert sub["status"] == "active"
    assert sub["client_id"] == client_ctx.user["id"]
    today = date.today()
    assert sub["start_date"] in {
        (today - timedelta(days=1)).isoformat(),
        today.isoformat(),
        (today + timedelta(days=1)).isoformat(),
    }
    assert sub["next_run_date"] == sub["start_date"]
    assert sub["occurrences_count"] == 0
    assert sub["category_name"] == "Limpieza Basica"


def test_create_subscription_with_start_date(client_ctx, limpieza_basica_category_id):
    future = (date.today() + timedelta(days=3)).isoformat()
    r = _create(client_ctx.session, limpieza_basica_category_id, start_date=future)
    assert r.status_code == 200
    sub = r.json()["subscription"]
    assert sub["start_date"] == future
    assert sub["next_run_date"] == future


def test_create_subscription_provider_rejected(provider_ctx, limpieza_basica_category_id):
    r = _create(provider_ctx.session, limpieza_basica_category_id)
    assert r.status_code == 422


def test_create_subscription_invalid_category(client_ctx):
    body = _payload("000000000000000000000000")
    r = client_ctx.session.post(f"{BASE_URL}/api/recurring/subscriptions", json=body)
    assert r.status_code == 404


# ----------------- LIST / OWNERSHIP -----------------
def test_list_only_returns_own_subscriptions(client_ctx, other_client_ctx, limpieza_basica_category_id):
    _create(client_ctx.session, limpieza_basica_category_id)
    _create(other_client_ctx.session, limpieza_basica_category_id)

    r = client_ctx.session.get(f"{BASE_URL}/api/recurring/subscriptions")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(item["client_id"] == client_ctx.user["id"] for item in d["items"])


def test_other_client_cannot_read_subscription(client_ctx, other_client_ctx, limpieza_basica_category_id):
    sub_id = _create(client_ctx.session, limpieza_basica_category_id).json()["subscription"]["id"]
    r = other_client_ctx.session.get(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}")
    assert r.status_code == 403


def test_other_client_cannot_cancel_subscription(client_ctx, other_client_ctx, limpieza_basica_category_id):
    sub_id = _create(client_ctx.session, limpieza_basica_category_id).json()["subscription"]["id"]
    r = other_client_ctx.session.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/cancel")
    assert r.status_code == 403


# ----------------- GENERATE -----------------
def test_generate_occurrence_weekly(client_ctx, limpieza_basica_category_id):
    start = date.today().isoformat()
    sub_id = _create(client_ctx.session, limpieza_basica_category_id, frequency="weekly", start_date=start).json()["subscription"]["id"]

    gen = client_ctx.session.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200, gen.text
    data = gen.json()
    assert data["occurrence"]["request_id"]
    assert data["occurrence"]["scheduled_date"] == start
    assert data["subscription"]["occurrences_count"] == 1
    assert data["subscription"]["next_run_date"] == (date.today() + timedelta(days=7)).isoformat()

    occ = client_ctx.session.get(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/occurrences")
    assert occ.status_code == 200
    body = occ.json()
    assert body["total"] == 1
    assert body["items"][0]["request_id"] == data["occurrence"]["request_id"]

    sr = client_ctx.session.get(f"{BASE_URL}/api/matching/service-requests/{data['occurrence']['request_id']}")
    assert sr.status_code == 200, sr.text


def test_generate_occurrence_biweekly(client_ctx, limpieza_basica_category_id):
    start = date.today().isoformat()
    sub_id = _create(client_ctx.session, limpieza_basica_category_id, frequency="biweekly", start_date=start).json()["subscription"]["id"]
    gen = client_ctx.session.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200
    assert gen.json()["subscription"]["next_run_date"] == (date.today() + timedelta(days=14)).isoformat()


def test_generate_occurrence_monthly(client_ctx, limpieza_basica_category_id):
    start = date.today().isoformat()
    sub_id = _create(client_ctx.session, limpieza_basica_category_id, frequency="monthly", start_date=start).json()["subscription"]["id"]
    gen = client_ctx.session.post(f"{BASE_URL}/api/recurring/subscriptions/{sub_id}/generate")
    assert gen.status_code == 200
    next_run = gen.json()["subscription"]["next_run_date"]
    assert next_run > start


# ----------------- PAUSE / RESUME / CANCEL -----------------
def test_pause_resume_cancel_flow(client_ctx, limpieza_basica_category_id):
    sub_id = _create(client_ctx.session, limpieza_basica_category_id).json()["subscription"]["id"]
    s = client_ctx.session
    base = f"{BASE_URL}/api/recurring/subscriptions/{sub_id}"

    assert s.post(f"{base}/pause").json()["subscription"]["status"] == "paused"
    assert s.post(f"{base}/generate").status_code == 409

    assert s.post(f"{base}/resume").json()["subscription"]["status"] == "active"
    assert s.post(f"{base}/generate").status_code == 200

    assert s.post(f"{base}/cancel").json()["subscription"]["status"] == "cancelled"
    assert s.post(f"{base}/pause").status_code == 409
    assert s.post(f"{base}/resume").status_code == 409
    assert s.post(f"{base}/generate").status_code == 409


# ----------------- REGRESIÓN: matching sigue funcionando -----------------
def test_regression_create_service_request(client_ctx, limpieza_basica_category_id):
    payload = {
        "client_id": client_ctx.user["id"],
        "category_id": limpieza_basica_category_id,
        "title": "Solicitud regresion",
        "description": "Prueba de regresion del flujo de solicitudes.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": "Roma Norte",
        "budget_amount": 400.0,
    }
    r = requests.post(f"{BASE_URL}/api/matching/service-requests", json=payload)
    assert r.status_code == 200, r.text
    assert "request" in r.json()


# ----------------- 404 -----------------
def test_subscription_not_found(client_ctx):
    r = client_ctx.session.get(f"{BASE_URL}/api/recurring/subscriptions/000000000000000000000000")
    assert r.status_code == 404

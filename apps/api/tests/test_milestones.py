"""Pruebas de integración de milestones + provider_dashboard (Xambas).

`/api/milestones/*` (salvo `/status` y `/files/*`) exige
``Authorization: Bearer <token>``; el cliente/proveedor sale del token.
`/api/provider/dashboard` todavía no lleva auth (pendiente).
"""
import uuid

import pytest
import requests

from tests.helpers import BASE_URL, authed_client, authed_provider


@pytest.fixture(scope="module")
def zone() -> str:
    return f"ZONA_MS_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def other_client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def provider_ctx(limpieza_basica_category_id: str, zone: str):
    return authed_provider(BASE_URL, limpieza_basica_category_id, [zone])


@pytest.fixture(scope="module")
def other_provider_ctx(limpieza_basica_category_id: str, zone: str):
    return authed_provider(BASE_URL, limpieza_basica_category_id, [zone + "_ALT"])


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def accepted_match(client_ctx, provider_ctx, zone, limpieza_basica_category_id):
    """service_request → matching → aceptar el match del proveedor.

    `/api/matching/*` todavía no lleva auth, así que se usa `requests` directo.
    """
    payload = {
        "client_id": client_ctx.user["id"],
        "category_id": limpieza_basica_category_id,
        "title": "TEST milestones request",
        "description": "Solicitud de prueba para milestones - limpieza basica.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": zone,
        "budget_amount": 1000.0,
    }
    r = requests.post(f"{BASE_URL}/api/matching/service-requests", json=payload)
    assert r.status_code == 200, r.text
    request_id = r.json()["request"]["id"]

    m = requests.get(f"{BASE_URL}/api/matching/service-requests/{request_id}/matches")
    assert m.status_code == 200, m.text
    mine = [x for x in m.json()["items"] if x["provider_user_id"] == provider_ctx.user["id"]]
    assert mine, f"Sin match para el proveedor en zona {zone}"
    match_id = mine[0]["id"]

    ac = requests.post(
        f"{BASE_URL}/api/matching/matches/{match_id}/accept",
        json={"provider_user_id": provider_ctx.user["id"]},
    )
    assert ac.status_code == 200, ac.text
    accepted = ac.json()
    assert accepted["status"] == "accepted"
    return {
        "match_id": match_id,
        "request_id": request_id,
        "provider_profile_id": accepted["provider_profile_id"],
        "provider_user_id": provider_ctx.user["id"],
        "client_id": client_ctx.user["id"],
    }


# ------------- STATUS (público) -------------
def test_status():
    r = requests.get(f"{BASE_URL}/api/milestones/status")
    assert r.status_code == 200
    assert r.json()["module"] == "milestones"


# ------------- AUTH -------------
def test_create_plan_requires_auth(accepted_match):
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans",
        json={"match_id": accepted_match["match_id"], "milestones": [{"title": "x", "amount": 10}]},
    )
    assert r.status_code == 401


def test_create_plan_provider_role_rejected(provider_ctx, accepted_match):
    r = provider_ctx.session.post(
        f"{BASE_URL}/api/milestones/plans",
        json={"match_id": accepted_match["match_id"], "milestones": [{"title": "x", "amount": 10}]},
    )
    assert r.status_code == 403


# ------------- CREATE PLAN -------------
@pytest.fixture(scope="module")
def plan(client_ctx, accepted_match):
    payload = {
        "match_id": accepted_match["match_id"],
        "currency": "MXN",
        "milestones": [
            {"title": "Etapa 1 - Preparacion", "amount": 300.0},
            {"title": "Etapa 2 - Entrega final", "amount": 700.0},
        ],
    }
    r = client_ctx.session.post(f"{BASE_URL}/api/milestones/plans", json=payload)
    assert r.status_code == 200, r.text
    p = r.json()["plan"]
    assert p["status"] == "active"
    assert p["total_amount"] == 1000.0
    assert p["client_id"] == client_ctx.user["id"]
    assert all(m["status"] == "pending" for m in p["milestones"])
    return p


def test_create_plan_duplicate_rejected(client_ctx, accepted_match, plan):
    r = client_ctx.session.post(
        f"{BASE_URL}/api/milestones/plans",
        json={"match_id": accepted_match["match_id"], "milestones": [{"title": "otra", "amount": 100.0}]},
    )
    assert r.status_code == 409


def test_release_before_submit_returns_409(client_ctx, plan):
    mid = plan["milestones"][0]["id"]
    r = client_ctx.session.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release"
    )
    assert r.status_code == 409, r.text


def test_submit_with_foreign_provider_returns_403(other_provider_ctx, plan, sample_image_bytes):
    mid = plan["milestones"][0]["id"]
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/submit",
        headers=_bearer(other_provider_ctx.token),
        files=[("files", ("photo.jpg", sample_image_bytes, "image/jpeg"))],
    )
    assert r.status_code == 403, r.text


# ------------- SUBMIT EVIDENCE -------------
def test_submit_evidence_ok(provider_ctx, plan, sample_image_bytes):
    mid = plan["milestones"][0]["id"]
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/submit",
        headers=_bearer(provider_ctx.token),
        files=[("files", ("photo.jpg", sample_image_bytes, "image/jpeg"))],
    )
    assert r.status_code == 200, r.text
    m0 = next(m for m in r.json()["plan"]["milestones"] if m["id"] == mid)
    assert m0["status"] == "submitted"
    assert m0["evidence"][0]["path"].startswith("xambas/milestones/")
    plan["_evidence_path"] = m0["evidence"][0]["path"]


# ------------- FILE SERVING (público) -------------
def test_get_file_ok(plan):
    path = plan.get("_evidence_path")
    assert path, "falta el path de evidencia; la prueba anterior falló"
    r = requests.get(f"{BASE_URL}/api/milestones/files/{path}")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")


def test_get_file_outside_prefix_404():
    r = requests.get(f"{BASE_URL}/api/milestones/files/xambas/ai-quote/whatever.jpg")
    assert r.status_code == 404


# ------------- RELEASE -------------
def test_release_with_foreign_client_returns_403(other_client_ctx, plan):
    mid = plan["milestones"][0]["id"]
    r = other_client_ctx.session.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release"
    )
    assert r.status_code == 403


def test_release_first_milestone(client_ctx, plan):
    mid = plan["milestones"][0]["id"]
    r = client_ctx.session.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release"
    )
    assert r.status_code == 200, r.text
    body = r.json()["plan"]
    m0 = next(m for m in body["milestones"] if m["id"] == mid)
    assert m0["status"] == "released"
    assert m0["transfer_mode"] == "manual"  # Stripe no configurado
    assert body["released_amount"] == 300.0
    assert body["status"] == "active"


def test_submit_and_release_second_milestone_completes_plan(client_ctx, provider_ctx, plan, sample_image_bytes):
    mid = plan["milestones"][1]["id"]
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/submit",
        headers=_bearer(provider_ctx.token),
        files=[("files", ("photo2.jpg", sample_image_bytes, "image/jpeg"))],
    )
    assert r.status_code == 200

    rel = client_ctx.session.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release"
    )
    assert rel.status_code == 200
    body = rel.json()["plan"]
    assert body["released_amount"] == 1000.0
    assert body["status"] == "completed"


# ------------- LIST PLANS (según el rol del token) -------------
def test_list_plans_as_client(client_ctx):
    r = client_ctx.session.get(f"{BASE_URL}/api/milestones/plans")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(p["client_id"] == client_ctx.user["id"] for p in d["items"])


def test_list_plans_as_provider(provider_ctx):
    r = provider_ctx.session.get(f"{BASE_URL}/api/milestones/plans")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(p["provider_user_id"] == provider_ctx.user["id"] for p in d["items"])


# ------------- PROVIDER DASHBOARD (sin auth todavía) -------------
def test_provider_dashboard(accepted_match):
    r = requests.get(
        f"{BASE_URL}/api/provider/dashboard",
        params={
            "provider_user_id": accepted_match["provider_user_id"],
            "provider_profile_id": accepted_match["provider_profile_id"],
        },
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["module"] == "provider_dashboard"
    m = d["metrics"]
    assert isinstance(m["commission_pct"], (int, float))
    assert m["accepted_jobs"] >= 1
    assert "recurring_visits" in d


def test_provider_dashboard_404(accepted_match):
    r = requests.get(
        f"{BASE_URL}/api/provider/dashboard",
        params={
            "provider_user_id": accepted_match["provider_user_id"],
            "provider_profile_id": "000000000000000000000000",
        },
    )
    assert r.status_code == 404

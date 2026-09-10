"""Pruebas de integración de los módulos milestones + provider_dashboard (Xambas)."""
import uuid

import pytest
import requests

from tests.helpers import BASE_URL, bootstrap_client, bootstrap_provider

# Las subidas multipart usan ``requests`` directo: la sesión ``api`` fija
# ``Content-Type: application/json``, que rompería el cuerpo multipart.


@pytest.fixture(scope="module")
def zone() -> str:
    return f"ZONA_MS_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def client_user() -> dict:
    return bootstrap_client(BASE_URL)


@pytest.fixture(scope="module")
def provider_user(limpieza_basica_category_id: str, zone: str) -> dict:
    return bootstrap_provider(
        BASE_URL, limpieza_basica_category_id, [zone], business_name="TEST MS Provider"
    )


@pytest.fixture(scope="module")
def other_provider_user(limpieza_basica_category_id: str, zone: str) -> dict:
    """Proveedor distinto, para probar los guardas 403."""
    return bootstrap_provider(
        BASE_URL, limpieza_basica_category_id, [zone + "_ALT"], business_name="TEST MS Provider Alt"
    )


@pytest.fixture(scope="module")
def accepted_match(api, client_user, provider_user, zone, limpieza_basica_category_id):
    """Crea service request, corre matching, encuentra y acepta el match del provider_user."""
    payload = {
        "client_id": client_user["id"],
        "category_id": limpieza_basica_category_id,
        "title": "TEST milestones request",
        "description": "Solicitud de prueba para milestones - limpieza basica.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": zone,
        "budget_amount": 1000.0,
    }
    r = api.post(f"{BASE_URL}/api/matching/service-requests", json=payload)
    assert r.status_code == 200, r.text
    request_id = r.json()["request"]["id"]

    m = api.get(f"{BASE_URL}/api/matching/service-requests/{request_id}/matches")
    assert m.status_code == 200, m.text
    matches = m.json()["items"]
    mine = [x for x in matches if x["provider_user_id"] == provider_user["id"]]
    assert mine, f"Sin match para el proveedor {provider_user['id']} en zona {zone}. Recibido: {matches}"
    match_id = mine[0]["id"]

    ac = api.post(
        f"{BASE_URL}/api/matching/matches/{match_id}/accept",
        json={"provider_user_id": provider_user["id"]},
    )
    assert ac.status_code == 200, ac.text
    accepted = ac.json()
    assert accepted["status"] == "accepted"
    return {
        "match_id": match_id,
        "request_id": request_id,
        "provider_profile_id": accepted["provider_profile_id"],
        "provider_user_id": provider_user["id"],
        "client_id": client_user["id"],
    }


# ------------- STATUS -------------
def test_status(api):
    r = api.get(f"{BASE_URL}/api/milestones/status")
    assert r.status_code == 200
    d = r.json()
    assert d["module"] == "milestones"
    assert d["status"] == "ready"


# ------------- CREATE PLAN -------------
@pytest.fixture(scope="module")
def plan(api, accepted_match):
    payload = {
        "match_id": accepted_match["match_id"],
        "client_id": accepted_match["client_id"],
        "currency": "MXN",
        "milestones": [
            {"title": "Etapa 1 - Preparacion", "amount": 300.0},
            {"title": "Etapa 2 - Entrega final", "amount": 700.0},
        ],
    }
    r = api.post(f"{BASE_URL}/api/milestones/plans", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["module"] == "milestones"
    p = body["plan"]
    assert p["status"] == "active"
    assert p["total_amount"] == 1000.0
    assert p["released_amount"] == 0.0
    assert len(p["milestones"]) == 2
    assert all(m["status"] == "pending" for m in p["milestones"])
    return p


def test_create_plan_duplicate_rejected(api, accepted_match, plan):
    payload = {
        "match_id": accepted_match["match_id"],
        "client_id": accepted_match["client_id"],
        "milestones": [{"title": "otra", "amount": 100.0}],
    }
    r = api.post(f"{BASE_URL}/api/milestones/plans", json=payload)
    assert r.status_code == 409


def test_release_before_submit_returns_409(api, accepted_match, plan):
    mid = plan["milestones"][0]["id"]
    r = api.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release",
        params={"client_id": accepted_match["client_id"]},
    )
    assert r.status_code == 409, r.text


def test_submit_with_foreign_provider_returns_403(api, accepted_match, plan, other_provider_user, sample_image_bytes):
    mid = plan["milestones"][0]["id"]
    files = [("files", ("photo.jpg", sample_image_bytes, "image/jpeg"))]
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/submit",
        params={"provider_user_id": other_provider_user["id"]},
        files=files,
    )
    assert r.status_code == 403, r.text


# ------------- SUBMIT EVIDENCE -------------
def test_submit_evidence_ok(api, accepted_match, plan, sample_image_bytes):
    mid = plan["milestones"][0]["id"]
    files = [("files", ("photo.jpg", sample_image_bytes, "image/jpeg"))]
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/submit",
        params={"provider_user_id": accepted_match["provider_user_id"]},
        files=files,
    )
    assert r.status_code == 200, r.text
    body = r.json()["plan"]
    m0 = next(m for m in body["milestones"] if m["id"] == mid)
    assert m0["status"] == "submitted"
    assert len(m0["evidence"]) == 1
    assert m0["evidence"][0]["path"].startswith("xambas/milestones/")
    assert m0["submitted_at"] is not None
    plan["_evidence_path"] = m0["evidence"][0]["path"]


# ------------- FILE SERVING -------------
def test_get_file_ok(api, plan):
    path = plan.get("_evidence_path")
    assert path, "falta el path de evidencia; la prueba anterior falló"
    r = api.get(f"{BASE_URL}/api/milestones/files/{path}")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 0


def test_get_file_outside_prefix_404(api):
    r = api.get(f"{BASE_URL}/api/milestones/files/xambas/ai-quote/whatever.jpg")
    assert r.status_code == 404


# ------------- RELEASE -------------
def test_release_with_foreign_client_returns_403(api, accepted_match, plan):
    mid = plan["milestones"][0]["id"]
    r = api.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release",
        params={"client_id": "000000000000000000000000"},
    )
    assert r.status_code == 403


def test_release_first_milestone(api, accepted_match, plan):
    mid = plan["milestones"][0]["id"]
    r = api.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release",
        params={"client_id": accepted_match["client_id"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()["plan"]
    m0 = next(m for m in body["milestones"] if m["id"] == mid)
    assert m0["status"] == "released"
    assert m0["transfer_mode"] == "manual"  # Stripe no configurado
    assert m0["released_at"] is not None
    assert body["released_amount"] == 300.0
    assert body["status"] == "active"


def test_submit_and_release_second_milestone_completes_plan(api, accepted_match, plan, sample_image_bytes):
    mid = plan["milestones"][1]["id"]
    files = [("files", ("photo2.jpg", sample_image_bytes, "image/jpeg"))]
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/submit",
        params={"provider_user_id": accepted_match["provider_user_id"]},
        files=files,
    )
    assert r.status_code == 200

    rel = api.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/release",
        params={"client_id": accepted_match["client_id"]},
    )
    assert rel.status_code == 200
    body = rel.json()["plan"]
    assert body["released_amount"] == 1000.0
    assert body["status"] == "completed"


# ------------- LIST PLANS -------------
def test_list_plans_by_client(api, accepted_match):
    r = api.get(f"{BASE_URL}/api/milestones/plans", params={"client_id": accepted_match["client_id"]})
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(p["client_id"] == accepted_match["client_id"] for p in d["items"])


def test_list_plans_by_provider(api, accepted_match):
    r = api.get(f"{BASE_URL}/api/milestones/plans", params={"provider_user_id": accepted_match["provider_user_id"]})
    assert r.status_code == 200
    assert r.json()["total"] >= 1


# ------------- PROVIDER DASHBOARD -------------
def test_provider_dashboard(api, accepted_match):
    r = api.get(
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
    assert "tier" in m
    assert isinstance(m["commission_pct"], (int, float))
    assert m["accepted_jobs"] >= 1
    assert "earnings_released" in m
    assert "earnings_in_escrow" in m
    assert "recurring_visits" in d


def test_provider_dashboard_404(api, accepted_match):
    r = api.get(
        f"{BASE_URL}/api/provider/dashboard",
        params={
            "provider_user_id": accepted_match["provider_user_id"],
            "provider_profile_id": "000000000000000000000000",
        },
    )
    assert r.status_code == 404

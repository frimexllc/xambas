"""Backend tests for Xambas milestones + provider_dashboard modules."""
import io
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://6a5a4228-856c-435a-9735-832a8c1fd2f3.preview.emergentagent.com").rstrip("/")
CATEGORY_ID_LIMPIEZA_BASICA = "6a7d4c75b514b1dcdaeafdd8"
SAMPLE_IMG = "/app/sample_kitchen.jpg"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def zone():
    return f"ZONA_MS_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def client_user(api):
    suffix = uuid.uuid4().hex[:8]
    r = api.post(f"{BASE_URL}/api/identity/bootstrap", json={
        "email": f"TEST_ms_cli_{suffix}@example.com",
        "phone": f"+52155600{suffix[:5]}",
        "role": "client",
        "locale": "es-MX",
    })
    assert r.status_code == 200, r.text
    return r.json()["user"]


@pytest.fixture(scope="module")
def provider_user(api, zone):
    suffix = uuid.uuid4().hex[:8]
    r = api.post(f"{BASE_URL}/api/identity/bootstrap", json={
        "email": f"TEST_ms_prov_{suffix}@example.com",
        "phone": f"+52155601{suffix[:5]}",
        "role": "provider",
        "locale": "es-MX",
        "provider_profile": {
            "business_name": "TEST MS Provider",
            "categories": [CATEGORY_ID_LIMPIEZA_BASICA],
            "coverage_zones": [zone],
        },
    })
    assert r.status_code == 200, r.text
    return r.json()["user"]


@pytest.fixture(scope="module")
def other_provider_user(api, zone):
    """A separate provider used to test 403 guards."""
    suffix = uuid.uuid4().hex[:8]
    r = api.post(f"{BASE_URL}/api/identity/bootstrap", json={
        "email": f"TEST_ms_prov2_{suffix}@example.com",
        "phone": f"+52155602{suffix[:5]}",
        "role": "provider",
        "locale": "es-MX",
        "provider_profile": {
            "business_name": "TEST MS Provider Alt",
            "categories": [CATEGORY_ID_LIMPIEZA_BASICA],
            "coverage_zones": [zone + "_ALT"],
        },
    })
    assert r.status_code == 200, r.text
    return r.json()["user"]


@pytest.fixture(scope="module")
def accepted_match(api, client_user, provider_user, zone):
    """Create service request, run matching, find and accept the match for provider_user."""
    payload = {
        "client_id": client_user["id"],
        "category_id": CATEGORY_ID_LIMPIEZA_BASICA,
        "title": "TEST milestones request",
        "description": "Solicitud de prueba para milestones - limpieza basica.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": zone,
        "budget_amount": 1000.0,
    }
    r = api.post(f"{BASE_URL}/api/matching/service-requests", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    request_id = body["request"]["id"]

    # get matches for this request
    m = api.get(f"{BASE_URL}/api/matching/service-requests/{request_id}/matches")
    assert m.status_code == 200, m.text
    matches = m.json()["items"]
    # pick match belonging to our provider
    mine = [x for x in matches if x["provider_user_id"] == provider_user["id"]]
    assert mine, f"No match found for provider {provider_user['id']} in zone {zone}. Got: {matches}"
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


def test_submit_with_foreign_provider_returns_403(api, accepted_match, plan, other_provider_user):
    mid = plan["milestones"][0]["id"]
    with open(SAMPLE_IMG, "rb") as fh:
        files = [("files", ("photo.jpg", fh.read(), "image/jpeg"))]
    r = requests.post(
        f"{BASE_URL}/api/milestones/plans/{plan['id']}/milestones/{mid}/submit",
        params={"provider_user_id": other_provider_user["id"]},
        files=files,
    )
    assert r.status_code == 403, r.text


# ------------- SUBMIT EVIDENCE -------------
def test_submit_evidence_ok(api, accepted_match, plan):
    mid = plan["milestones"][0]["id"]
    with open(SAMPLE_IMG, "rb") as fh:
        files = [("files", ("photo.jpg", fh.read(), "image/jpeg"))]
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
    assert path, "evidence path missing; previous test failed"
    r = requests.get(f"{BASE_URL}/api/milestones/files/{path}")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 0


def test_get_file_outside_prefix_404(api):
    # No leading "xambas/milestones/" prefix -> 404
    r = requests.get(f"{BASE_URL}/api/milestones/files/xambas/ai-quote/whatever.jpg")
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
    assert m0["transfer_mode"] == "manual"  # Stripe not configured
    assert m0["released_at"] is not None
    assert body["released_amount"] == 300.0
    assert body["status"] == "active"  # 1 pending remaining


def test_submit_and_release_second_milestone_completes_plan(api, accepted_match, plan):
    mid = plan["milestones"][1]["id"]
    with open(SAMPLE_IMG, "rb") as fh:
        files = [("files", ("photo2.jpg", fh.read(), "image/jpeg"))]
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
    d = r.json()
    assert d["total"] >= 1


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
    assert "commission_pct" in m
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

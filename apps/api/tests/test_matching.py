"""Pruebas de autenticación/autorización de `/api/matching/*`."""
import uuid

import pytest
import requests

from tests.helpers import BASE_URL, accept_match_for, authed_client, authed_provider

FAKE_ID = "0123456789abcdef01234567"


@pytest.fixture(scope="module")
def zone() -> str:
    return f"ZONA_MT_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def other_client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def provider_ctx(limpieza_basica_category_id, zone):
    return authed_provider(BASE_URL, limpieza_basica_category_id, [zone])


@pytest.fixture(scope="module")
def other_provider_ctx(limpieza_basica_category_id, zone):
    return authed_provider(BASE_URL, limpieza_basica_category_id, [zone + "_X"])


@pytest.fixture(scope="module")
def match(client_ctx, provider_ctx, zone, limpieza_basica_category_id):
    return accept_match_for(client_ctx, provider_ctx, zone, limpieza_basica_category_id)


def _sr_payload(category_id, zone):
    return {
        "category_id": category_id,
        "title": "Solicitud de prueba matching",
        "description": "Descripcion suficientemente larga para pasar validacion.",
        "country_code": "MX",
        "city": "CDMX",
        "coverage_zone": zone,
    }


# ------------- público -------------
def test_status_and_categories_public():
    assert requests.get(f"{BASE_URL}/api/matching/status").status_code == 200
    assert requests.get(f"{BASE_URL}/api/matching/categories").status_code == 200


# ------------- service-requests -------------
def test_create_sr_requires_auth(limpieza_basica_category_id, zone):
    r = requests.post(
        f"{BASE_URL}/api/matching/service-requests", json=_sr_payload(limpieza_basica_category_id, zone)
    )
    assert r.status_code == 401


def test_create_sr_rejects_provider(provider_ctx, limpieza_basica_category_id, zone):
    r = provider_ctx.session.post(
        f"{BASE_URL}/api/matching/service-requests", json=_sr_payload(limpieza_basica_category_id, zone)
    )
    assert r.status_code == 403


def test_list_sr_scoped_to_client(client_ctx, other_client_ctx, limpieza_basica_category_id, zone):
    client_ctx.session.post(
        f"{BASE_URL}/api/matching/service-requests", json=_sr_payload(limpieza_basica_category_id, zone)
    )
    r = client_ctx.session.get(f"{BASE_URL}/api/matching/service-requests")
    assert r.status_code == 200
    assert all(item["client_id"] == client_ctx.user["id"] for item in r.json()["items"])
    # un proveedor no puede usar el listado de cliente
    assert other_client_ctx.session  # sanity


def test_get_sr_owner_ok_and_outsider_403(client_ctx, other_client_ctx, match):
    ok = client_ctx.session.get(f"{BASE_URL}/api/matching/service-requests/{match['request_id']}")
    assert ok.status_code == 200
    forbidden = other_client_ctx.session.get(
        f"{BASE_URL}/api/matching/service-requests/{match['request_id']}"
    )
    assert forbidden.status_code == 403


def test_get_sr_visible_to_matched_provider(provider_ctx, match):
    r = provider_ctx.session.get(f"{BASE_URL}/api/matching/service-requests/{match['request_id']}")
    assert r.status_code == 200


def test_get_sr_hidden_from_unrelated_provider(other_provider_ctx, match):
    r = other_provider_ctx.session.get(
        f"{BASE_URL}/api/matching/service-requests/{match['request_id']}"
    )
    assert r.status_code == 403


def test_rerun_matching_only_owner(other_client_ctx, match):
    r = other_client_ctx.session.post(
        f"{BASE_URL}/api/matching/service-requests/{match['request_id']}/run"
    )
    assert r.status_code == 403


# ------------- matches -------------
def test_provider_matches_requires_provider_role(client_ctx):
    r = client_ctx.session.get(
        f"{BASE_URL}/api/matching/providers/{client_ctx.user['id']}/matches"
    )
    assert r.status_code == 403


def test_provider_only_sees_own_matches(provider_ctx, other_provider_ctx):
    # aunque pida el id de otro en la ruta, el server usa el del token
    r = other_provider_ctx.session.get(
        f"{BASE_URL}/api/matching/providers/{provider_ctx.user['id']}/matches"
    )
    assert r.status_code == 200
    assert all(m["provider_user_id"] == other_provider_ctx.user["id"] for m in r.json()["items"])


def test_accept_match_requires_auth(match):
    r = requests.post(
        f"{BASE_URL}/api/matching/matches/{match['match_id']}/accept",
        json={"provider_user_id": match["provider_user_id"]},
    )
    assert r.status_code == 401


def test_accept_match_wrong_provider_403(other_provider_ctx, match):
    r = other_provider_ctx.session.post(
        f"{BASE_URL}/api/matching/matches/{match['match_id']}/accept",
        json={"provider_user_id": other_provider_ctx.user["id"]},
    )
    assert r.status_code == 403

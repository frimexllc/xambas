"""Pruebas de la capa de autenticación/autorización de `/api/billing/*`.

Cubren los guardas de token y rol; el camino feliz de pagos necesita Stripe
y se valida aparte (no en CI).
"""
import pytest
import requests

from tests.helpers import BASE_URL, authed_client, authed_provider


@pytest.fixture(scope="module")
def client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def provider_ctx(limpieza_basica_category_id: str):
    return authed_provider(BASE_URL, limpieza_basica_category_id, ["Billing Zone"])


@pytest.fixture(scope="module")
def other_provider_ctx(limpieza_basica_category_id: str):
    return authed_provider(BASE_URL, limpieza_basica_category_id, ["Billing Zone Alt"])


def _provider_profile_id(ctx) -> str:
    r = requests.get(f"{BASE_URL}/api/identity/users/{ctx.user['id']}")
    r.raise_for_status()
    return r.json()["provider_profile"]["id"]


# ------------- endpoints públicos -------------
def test_status_and_tiers_are_public():
    assert requests.get(f"{BASE_URL}/api/billing/status").status_code == 200
    assert requests.get(f"{BASE_URL}/api/billing/tiers").status_code == 200


# ------------- pagos: auth -------------
FAKE_ID = "0123456789abcdef01234567"


def test_create_payment_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/billing/payments", json={"match_id": FAKE_ID, "job_amount": 100}
    )
    assert r.status_code == 401


def test_create_payment_rejects_provider_role(provider_ctx):
    r = provider_ctx.session.post(
        f"{BASE_URL}/api/billing/payments", json={"match_id": FAKE_ID, "job_amount": 100}
    )
    assert r.status_code == 403


def test_list_payments_requires_auth():
    assert requests.get(f"{BASE_URL}/api/billing/payments").status_code == 401


def test_list_payments_scoped_to_caller(client_ctx, provider_ctx):
    # ambos roles obtienen su propia vista (vacía es válido)
    rc = client_ctx.session.get(f"{BASE_URL}/api/billing/payments")
    assert rc.status_code == 200
    assert rc.json()["module"] == "billing"
    rp = provider_ctx.session.get(f"{BASE_URL}/api/billing/payments")
    assert rp.status_code == 200


def test_get_payment_not_found(client_ctx):
    r = client_ctx.session.get(f"{BASE_URL}/api/billing/payments/{FAKE_ID}")
    assert r.status_code == 404


def test_confirm_completion_requires_auth():
    assert (
        requests.post(f"{BASE_URL}/api/billing/payments/{FAKE_ID}/confirm-completion").status_code
        == 401
    )


def test_confirm_completion_rejects_provider_role(provider_ctx):
    r = provider_ctx.session.post(
        f"{BASE_URL}/api/billing/payments/{FAKE_ID}/confirm-completion"
    )
    assert r.status_code == 403


# ------------- Stripe Connect: auth + propiedad -------------
def test_onboarding_requires_auth():
    r = requests.post(
        f"{BASE_URL}/api/billing/connect/onboarding-link", json={"provider_profile_id": FAKE_ID}
    )
    assert r.status_code == 401


def test_onboarding_rejects_client_role(client_ctx):
    r = client_ctx.session.post(
        f"{BASE_URL}/api/billing/connect/onboarding-link", json={"provider_profile_id": FAKE_ID}
    )
    assert r.status_code == 403


def test_onboarding_rejects_foreign_profile(provider_ctx, other_provider_ctx):
    foreign = _provider_profile_id(other_provider_ctx)
    r = provider_ctx.session.post(
        f"{BASE_URL}/api/billing/connect/onboarding-link", json={"provider_profile_id": foreign}
    )
    assert r.status_code == 403


def test_connect_status_own_profile_ok(provider_ctx):
    own = _provider_profile_id(provider_ctx)
    r = provider_ctx.session.get(
        f"{BASE_URL}/api/billing/connect/status", params={"provider_profile_id": own}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["provider_profile_id"] == own
    assert body["stripe_connect_account_id"] is None  # aún sin onboarding


def test_connect_status_foreign_profile_403(provider_ctx, other_provider_ctx):
    foreign = _provider_profile_id(other_provider_ctx)
    r = provider_ctx.session.get(
        f"{BASE_URL}/api/billing/connect/status", params={"provider_profile_id": foreign}
    )
    assert r.status_code == 403

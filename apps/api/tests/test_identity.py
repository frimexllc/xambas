"""Pruebas del login de cuentas existentes: `POST /api/identity/login`."""
import requests

from tests.helpers import BASE_URL, bootstrap_client


def _complete_otp(user_id: str, challenge_id: str, code: str) -> dict:
    r = requests.post(
        f"{BASE_URL}/api/identity/otp/verify",
        json={
            "user_id": user_id,
            "challenge_id": challenge_id,
            "code": code,
            "device_name": "pytest-login",
        },
    )
    return r


def test_login_unknown_identifier_404():
    r = requests.post(
        f"{BASE_URL}/api/identity/login", json={"identifier": "+520000000000000"}
    )
    assert r.status_code == 404


def test_login_by_phone_then_verify_creates_session():
    user = bootstrap_client(BASE_URL)

    r = requests.post(
        f"{BASE_URL}/api/identity/login", json={"identifier": user["phone"]}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_id"] == user["id"]
    assert body["challenge_id"]
    assert body["debug_code"]  # modo dev

    v = _complete_otp(user["id"], body["challenge_id"], body["debug_code"])
    assert v.status_code == 200, v.text
    session = v.json()["session"]
    assert session["token"]

    # el token sirve en un endpoint autenticado
    me = requests.get(
        f"{BASE_URL}/api/recurring/subscriptions",
        headers={"Authorization": f"Bearer {session['token']}"},
    )
    assert me.status_code == 200


def test_login_by_email_works_too():
    user = bootstrap_client(BASE_URL)
    r = requests.post(
        f"{BASE_URL}/api/identity/login", json={"identifier": user["email"].upper()}
    )
    assert r.status_code == 200, r.text
    assert r.json()["user_id"] == user["id"]


# ----------------- RATE LIMITING -----------------
# El límite exacto es configuración (OTP_REQUEST_LIMIT_PER_USER / LOGIN_LIMIT_PER_IDENTIFIER),
# así que estas pruebas no asumen un número concreto: repiten hasta ver un 429
# y verifican que al menos una llamada pasó antes de que se activara el límite.

def test_otp_request_rate_limited_per_user():
    user = bootstrap_client(BASE_URL)
    statuses = []
    for _ in range(20):
        r = requests.post(
            f"{BASE_URL}/api/identity/otp/request",
            json={"user_id": user["id"], "purpose": "login"},
        )
        statuses.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in statuses, f"esperaba un 429 en algún punto, obtuve: {statuses}"
    assert statuses.count(200) >= 1


def test_login_rate_limited_per_identifier():
    user = bootstrap_client(BASE_URL)
    statuses = []
    for _ in range(20):
        r = requests.post(
            f"{BASE_URL}/api/identity/login", json={"identifier": user["phone"]}
        )
        statuses.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in statuses, f"esperaba un 429 en algún punto, obtuve: {statuses}"
    assert statuses.count(200) >= 1


def test_rate_limit_is_scoped_per_user_not_global():
    # agotar el límite de un usuario no debe afectar a otro
    exhausted_user = bootstrap_client(BASE_URL)
    for _ in range(20):
        r = requests.post(
            f"{BASE_URL}/api/identity/otp/request",
            json={"user_id": exhausted_user["id"], "purpose": "login"},
        )
        if r.status_code == 429:
            break

    other_user = bootstrap_client(BASE_URL)
    r = requests.post(
        f"{BASE_URL}/api/identity/otp/request",
        json={"user_id": other_user["id"], "purpose": "login"},
    )
    assert r.status_code == 200, r.text

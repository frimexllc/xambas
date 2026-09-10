"""Helpers compartidos por la suite de integración.

La lógica de fixtures vive en ``conftest.py``; aquí van solo funciones puras y
constantes para que los módulos de prueba las importen sin el anti-patrón de
``from tests.conftest import ...``.
"""
from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

import requests

DEFAULT_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = (10, 90)  # (connect, read); la visión de Groq puede tardar ~10s

# Nombre de la subcategoría que usan matching + recurring + milestones. Debe
# existir en app/modules/matching/seeds.py.
LIMPIEZA_BASICA = "Limpieza Basica"


def resolve_base_url() -> str:
    for env_var in ("XAMBAS_API_URL", "REACT_APP_BACKEND_URL"):
        value = os.environ.get(env_var)
        if value:
            return value.rstrip("/")
    return DEFAULT_BASE_URL


def run_external_enabled() -> bool:
    """Las pruebas marcadas ``external`` hacen llamadas reales a Groq (red + costo).

    Se saltan salvo que ``XAMBAS_RUN_EXTERNAL_TESTS`` esté en 1/true/yes.
    """
    return os.environ.get("XAMBAS_RUN_EXTERNAL_TESTS", "").lower() in {"1", "true", "yes"}


BASE_URL = resolve_base_url()


def bootstrap_client(base_url: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"TEST_client_{suffix}@example.com",
        "phone": f"+52155512{suffix[:5]}",
        "role": "client",
        "locale": "es-MX",
    }
    r = requests.post(f"{base_url}/api/identity/bootstrap", json=payload, timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["user"]


def bootstrap_provider(
    base_url: str,
    category_id: str,
    coverage_zones: list[str],
    *,
    business_name: str = "TEST Provider",
) -> dict:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"TEST_prov_{suffix}@example.com",
        "phone": f"+52155513{suffix[:5]}",
        "role": "provider",
        "locale": "es-MX",
        "provider_profile": {
            "business_name": business_name,
            "categories": [category_id],
            "coverage_zones": coverage_zones,
        },
    }
    r = requests.post(f"{base_url}/api/identity/bootstrap", json=payload, timeout=REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["user"]


def verify_otp_for(base_url: str, user_id: str) -> str:
    """Completa el flujo OTP en modo dev y devuelve el token de sesión.

    El código llega como ``debug_code`` en la respuesta de `otp/request`.
    """
    r = requests.post(
        f"{base_url}/api/identity/otp/request",
        json={"user_id": user_id, "purpose": "registration", "channel": "sms"},
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    challenge_id = body["challenge"]["id"] if "challenge" in body else body.get("challenge_id")
    code = body.get("debug_code") or body.get("challenge", {}).get("debug_code")
    assert code, f"sin debug_code en la respuesta: {body}"
    r = requests.post(
        f"{base_url}/api/identity/otp/verify",
        json={
            "user_id": user_id,
            "challenge_id": challenge_id,
            "code": code,
            "device_name": "pytest",
        },
        timeout=REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    return r.json()["session"]["token"]


def _authed_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    return session


def authed_client(base_url: str) -> SimpleNamespace:
    """Cliente registrado + verificado, con una `requests.Session` que ya lleva
    el header ``Authorization: Bearer <token>``.
    """
    user = bootstrap_client(base_url)
    token = verify_otp_for(base_url, user["id"])
    return SimpleNamespace(user=user, token=token, session=_authed_session(token))


def authed_provider(base_url: str, category_id: str, coverage_zones: list[str]) -> SimpleNamespace:
    user = bootstrap_provider(base_url, category_id, coverage_zones)
    token = verify_otp_for(base_url, user["id"])
    return SimpleNamespace(user=user, token=token, session=_authed_session(token))

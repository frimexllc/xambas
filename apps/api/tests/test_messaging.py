"""Pruebas de autenticación/autorización de `/api/messaging/*`."""
import uuid

import pytest
import requests

from tests.helpers import BASE_URL, accept_match_for, authed_client, authed_provider


@pytest.fixture(scope="module")
def zone() -> str:
    return f"ZONA_MSG_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def client_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def provider_ctx(limpieza_basica_category_id, zone):
    return authed_provider(BASE_URL, limpieza_basica_category_id, [zone])


@pytest.fixture(scope="module")
def outsider_ctx():
    return authed_client(BASE_URL)


@pytest.fixture(scope="module")
def match(client_ctx, provider_ctx, zone, limpieza_basica_category_id):
    return accept_match_for(client_ctx, provider_ctx, zone, limpieza_basica_category_id)


@pytest.fixture(scope="module")
def thread(client_ctx, match):
    r = client_ctx.session.post(
        f"{BASE_URL}/api/messaging/threads", json={"match_id": match["match_id"]}
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_status_public():
    assert requests.get(f"{BASE_URL}/api/messaging/status").status_code == 200


def test_create_thread_requires_auth(match):
    r = requests.post(
        f"{BASE_URL}/api/messaging/threads", json={"match_id": match["match_id"]}
    )
    assert r.status_code == 401


def test_outsider_cannot_open_thread(outsider_ctx, match):
    r = outsider_ctx.session.post(
        f"{BASE_URL}/api/messaging/threads", json={"match_id": match["match_id"]}
    )
    assert r.status_code == 403


def test_participants_can_read(client_ctx, provider_ctx, thread):
    assert client_ctx.session.get(
        f"{BASE_URL}/api/messaging/threads/{thread['id']}/messages"
    ).status_code == 200
    assert provider_ctx.session.get(
        f"{BASE_URL}/api/messaging/threads/{thread['id']}/messages"
    ).status_code == 200


def test_outsider_cannot_read(outsider_ctx, thread):
    r = outsider_ctx.session.get(f"{BASE_URL}/api/messaging/threads/{thread['id']}/messages")
    assert r.status_code == 403


def test_message_attributed_to_token_user_not_body(client_ctx, provider_ctx, thread):
    # el cliente miente sobre sender_id/sender_role → el server usa el token
    r = client_ctx.session.post(
        f"{BASE_URL}/api/messaging/threads/{thread['id']}/messages",
        json={"sender_id": provider_ctx.user["id"], "sender_role": "provider", "body": "hola"},
    )
    assert r.status_code == 200, r.text
    msg = r.json()
    assert msg["sender_id"] == client_ctx.user["id"]
    assert msg["sender_role"] == "client"


def test_outsider_cannot_post(outsider_ctx, thread):
    r = outsider_ctx.session.post(
        f"{BASE_URL}/api/messaging/threads/{thread['id']}/messages",
        json={"sender_id": outsider_ctx.user["id"], "sender_role": "client", "body": "colado"},
    )
    assert r.status_code == 403

"""End-to-end auth flow through the API gateway.

Run against a running stack:
    docker run --rm --network oncogon-net -e GATEWAY_URL=http://oncogon-gateway:8000 \
      -v "$PWD/services/auth/tests:/tests" python:3.12-slim \
      sh -c "pip -q install pytest httpx && pytest -q /tests"
"""

import os
import uuid

import httpx
import pytest

BASE = os.environ.get("GATEWAY_URL", "http://localhost:8000") + "/api/v1/auth"
PASSWORD = "Oncology2026"


@pytest.fixture
def client():
    # Unique X-Forwarded-For per test keeps the gateway rate limiter from interfering.
    with httpx.Client(base_url=BASE, timeout=10, headers={"x-forwarded-for": f"10.0.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"}) as c:
        yield c


def new_email() -> str:
    return f"nomsa.{uuid.uuid4().hex[:10]}@example.org"


def register(client: httpx.Client, email: str) -> dict:
    r = client.post("/register", json={"full_name": "Nomsa Dlamini", "email": email, "password": PASSWORD, "institution": "UCT"})
    assert r.status_code == 201, r.text
    return r.json()


def test_register_login_me(client):
    email = new_email()
    body = register(client, email)
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "researcher"
    assert body["tokens"]["token_type"] == "bearer"

    r = client.post("/login", json={"email": email.upper(), "password": PASSWORD})
    assert r.status_code == 200, r.text
    access = r.json()["tokens"]["access_token"]

    r = client.get("/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Nomsa Dlamini"


def test_duplicate_and_validation(client):
    email = new_email()
    register(client, email)
    r = client.post("/register", json={"full_name": "Someone", "email": email, "password": PASSWORD})
    assert r.status_code == 409

    r = client.post("/register", json={"full_name": "Weak", "email": new_email(), "password": "short"})
    assert r.status_code == 422
    assert "8 characters" in r.json()["detail"]

    r = client.post("/register", json={"full_name": "Admin", "email": new_email(), "password": PASSWORD, "role": "platform_admin"})
    assert r.status_code == 422  # privileged roles are not self-service


def test_wrong_password_and_lockout(client):
    email = new_email()
    register(client, email)
    for _ in range(5):
        r = client.post("/login", json={"email": email, "password": "Wrong12345"})
        assert r.status_code == 401
    r = client.post("/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 423

    r = client.post("/login", json={"email": new_email(), "password": PASSWORD})
    assert r.status_code == 401


def test_refresh_rotation_and_reuse_detection(client):
    tokens = register(client, new_email())["tokens"]
    first = tokens["refresh_token"]

    r = client.post("/refresh", json={"refresh_token": first})
    assert r.status_code == 200
    second = r.json()["refresh_token"]
    assert second != first

    # Replaying the rotated token revokes the whole family, including `second`.
    assert client.post("/refresh", json={"refresh_token": first}).status_code == 401
    assert client.post("/refresh", json={"refresh_token": second}).status_code == 401


def test_logout_revokes_refresh(client):
    tokens = register(client, new_email())["tokens"]
    assert client.post("/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post("/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_password_reset_flow(client):
    email = new_email()
    tokens = register(client, email)["tokens"]

    r = client.post("/password/forgot", json={"email": email})
    assert r.status_code == 202
    code = r.json()["debug_code"]
    assert code and len(code) == 6

    wrong = "000000" if code != "000000" else "111111"
    assert client.post("/password/verify", json={"email": email, "code": wrong}).status_code == 400

    r = client.post("/password/verify", json={"email": email, "code": code})
    assert r.status_code == 200
    reset_token = r.json()["reset_token"]

    # A code works only once.
    assert client.post("/password/verify", json={"email": email, "code": code}).status_code == 400

    r = client.post("/password/reset", json={"reset_token": reset_token, "new_password": "NewPassword99"})
    assert r.status_code == 204

    assert client.post("/login", json={"email": email, "password": PASSWORD}).status_code == 401
    assert client.post("/login", json={"email": email, "password": "NewPassword99"}).status_code == 200
    # Old sessions were signed out.
    assert client.post("/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_forgot_unknown_email_does_not_leak(client):
    r = client.post("/password/forgot", json={"email": new_email()})
    assert r.status_code == 202
    assert r.json()["debug_code"] is None


def test_me_requires_token(client):
    assert client.get("/me").status_code in (401, 403)
    assert client.get("/me", headers={"Authorization": "Bearer nope"}).status_code == 401

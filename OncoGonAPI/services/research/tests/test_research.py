"""Research service tests, in-process against the mock repository (no Docker needed).

    pip install -r requirements-dev.txt && pytest -q tests
"""

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 40)

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import MockResearchRepository

client = TestClient(app)
PROJECT, EXPERIMENT = "OGC-CO-014", "EXP-CO-014-017"


def token(typ: str = "access", ttl: timedelta = timedelta(minutes=5)) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": "user-1", "iss": "oncogon-auth", "aud": "oncogon-api", "iat": now, "exp": now + ttl, "typ": typ, "role": "researcher"}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


AUTH = {"Authorization": f"Bearer {token()}"}


def get(path: str, **params):
    return client.get(f"/research{path}", headers=AUTH, params=params)


def test_health_reports_simulated_data():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["data_mode"] == "SIMULATED"


@pytest.mark.parametrize("headers", [{}, {"Authorization": f"Bearer {token(typ='password_reset')}"}, {"Authorization": f"Bearer {token(ttl=timedelta(minutes=-1))}"}])
def test_requires_valid_access_token(headers):
    assert client.get("/research/workspace", headers=headers).status_code == 401


def test_workspace_joins_project_experiment_and_supervisor():
    r = get("/workspace")
    assert r.status_code == 200
    assert r.headers["X-Data-Mode"] == "SIMULATED"
    body = r.json()
    assert body["project"]["id"] == PROJECT
    assert body["experiment"]["id"] == EXPERIMENT
    assert body["supervisor"]["name"] == "Professor Anna"
    assert body["meta"] == {**body["meta"], "data_mode": "SIMULATED", "training_eligible": False}


@pytest.mark.parametrize(
    "path",
    [
        "/projects",
        f"/projects/{PROJECT}",
        f"/projects/{PROJECT}/experiments",
        f"/projects/{PROJECT}/files",
        f"/projects/{PROJECT}/conversations",
        f"/projects/{PROJECT}/instruction",
        f"/projects/{PROJECT}/memory",
        f"/projects/{PROJECT}/tasks",
        f"/projects/{PROJECT}/meeting-draft",
        f"/experiments/{EXPERIMENT}",
        f"/experiments/{EXPERIMENT}/analysis",
        f"/experiments/{EXPERIMENT}/next-step",
        f"/experiments/{EXPERIMENT}/note-draft",
        f"/experiments/{EXPERIMENT}/uploads/latest",
        "/catalog/evidence-types",
        "/catalog/apps",
        "/catalog/voice-commands",
    ],
)
def test_every_endpoint_serves_mock_data(path):
    r = get(path)
    assert r.status_code == 200, r.text
    assert r.json()


def test_instruction_and_meeting_draft_embed_supervisor():
    assert get(f"/projects/{PROJECT}/instruction").json()["supervisor"]["id"] == "anna"
    assert get(f"/projects/{PROJECT}/meeting-draft").json()["recipient"]["name"] == "Professor Anna"


def test_memory_filters_by_category_and_query():
    results = get(f"/projects/{PROJECT}/memory", category="Results").json()
    assert {m["id"] for m in results} == {"m1", "m7"}
    assert [m["id"] for m in get(f"/projects/{PROJECT}/memory", q="prof. anna").json()] == ["m6"]


def test_next_step_requires_supervisor_approval():
    assert get(f"/experiments/{EXPERIMENT}/next-step").json()["requires_supervisor_approval"] is True


@pytest.mark.parametrize("path", ["/projects/NOPE", "/projects/NOPE/tasks", "/experiments/NOPE/analysis"])
def test_unknown_ids_return_404(path):
    r = get(path)
    assert r.status_code == 404 and r.json()["detail"].endswith("not found.")


def test_repository_returns_copies():
    repo = MockResearchRepository()
    repo.get_project(PROJECT)["title"] = "changed"
    assert repo.get_project(PROJECT)["title"] == "Compound X / Cervical Cancer"

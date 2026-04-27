"""Admin /cognition/decision/active endpoints (mode toggle)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.admin.router import create_admin_router
from cognition.engines.decision_engine import set_active_mode


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("COGNITION_DECISION_USE_LLM", raising=False)
    set_active_mode(None)
    yield
    set_active_mode(None)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(create_admin_router(component_name="test"))
    return TestClient(app)


def test_default_is_heuristic_from_env(client: TestClient):
    r = client.get("/admin/cognition/decision/active")
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": True, "mode": "heuristic", "source": "env", "message": None}


def test_env_var_reflected(client: TestClient, monkeypatch):
    monkeypatch.setenv("COGNITION_DECISION_USE_LLM", "true")
    r = client.get("/admin/cognition/decision/active")
    body = r.json()
    assert body["mode"] == "llm"
    assert body["source"] == "env"


def test_post_sets_override(client: TestClient):
    r = client.post("/admin/cognition/decision/active", json={"mode": "llm"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "llm"
    assert body["source"] == "override"
    # Subsequent GET reflects override
    r2 = client.get("/admin/cognition/decision/active")
    assert r2.json()["mode"] == "llm"
    assert r2.json()["source"] == "override"


def test_post_invalid_mode_400(client: TestClient):
    r = client.post("/admin/cognition/decision/active", json={"mode": "telepathy"})
    assert r.status_code == 422  # FastAPI validation


def test_delete_clears_override_back_to_env(client: TestClient, monkeypatch):
    monkeypatch.setenv("COGNITION_DECISION_USE_LLM", "true")
    client.post("/admin/cognition/decision/active", json={"mode": "heuristic"})
    assert client.get("/admin/cognition/decision/active").json()["mode"] == "heuristic"
    r = client.delete("/admin/cognition/decision/active")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "llm"  # back to env
    assert body["source"] == "env"

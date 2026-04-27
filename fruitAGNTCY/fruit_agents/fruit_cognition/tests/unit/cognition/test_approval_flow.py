"""Approval flow: inbox + approve/reject/request-alternative endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cognition.api.router import create_cognition_router
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract, IntentStatus
from cognition.services.cognition_fabric import get_fabric, reset_fabric


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("COGNITION_PG_DSN", raising=False)
    reset_fabric()
    yield
    reset_fabric()


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(create_cognition_router())
    return TestClient(app)


def _seed_pending_intent() -> IntentContract:
    """Intent whose current decision will require approval (high weather risk)."""
    intent = IntentContract(
        goal="x",
        fruit_type="mango",
        quantity_lb=200,
        max_price_usd=2000,
        delivery_days=10,
        human_approval_required_if=["weather_risk_high"],
    )
    f = get_fabric()
    f.save_intent(intent)
    f.save_claim(Claim(
        intent_id=intent.intent_id, agent_id="colombia-farm",
        claim_type="inventory", subject="mango",
        value={"available_lb": 500, "origin": "colombia"},
    ))
    f.save_claim(Claim(
        intent_id=intent.intent_id, agent_id="colombia-farm",
        claim_type="price", subject="mango", value={"unit_price_usd": 2.0},
    ))
    f.save_claim(Claim(
        intent_id=intent.intent_id, agent_id="colombia-farm",
        claim_type="quality", subject="mango", value={"quality_score": 0.9},
    ))
    f.save_claim(Claim(
        intent_id=intent.intent_id, agent_id="weather-mcp",
        claim_type="weather_risk", subject="colombia",
        value={"region": "colombia", "weather_risk_score": 0.8},
    ))
    return intent


def _seed_clean_intent() -> IntentContract:
    """Intent whose decision is allowed without approval."""
    intent = IntentContract(
        goal="x", fruit_type="apple", quantity_lb=200, max_price_usd=2000,
    )
    f = get_fabric()
    f.save_intent(intent)
    f.save_claim(Claim(
        intent_id=intent.intent_id, agent_id="brazil-farm",
        claim_type="inventory", subject="apple",
        value={"available_lb": 500, "origin": "brazil"},
    ))
    f.save_claim(Claim(
        intent_id=intent.intent_id, agent_id="brazil-farm",
        claim_type="price", subject="apple", value={"unit_price_usd": 1.0},
    ))
    f.save_claim(Claim(
        intent_id=intent.intent_id, agent_id="brazil-farm",
        claim_type="quality", subject="apple", value={"quality_score": 0.9},
    ))
    return intent


# ----- inbox -----


def test_inbox_empty_when_no_intents(client: TestClient):
    r = client.get("/cognition/approvals")
    assert r.status_code == 200
    assert r.json() == []


def test_inbox_includes_only_pending(client: TestClient):
    pending = _seed_pending_intent()
    _seed_clean_intent()
    r = client.get("/cognition/approvals")
    body = r.json()
    intent_ids = [item["intent"]["intent_id"] for item in body]
    assert intent_ids == [pending.intent_id]
    assert body[0]["decision"]["requires_human_approval"] is True
    assert "weather_risk_high" in body[0]["decision"]["approval_violations"]


def test_inbox_promotes_status_to_approval_required(client: TestClient):
    pending = _seed_pending_intent()
    assert get_fabric().get_intent(pending.intent_id).status == IntentStatus.DRAFT
    client.get("/cognition/approvals")
    assert get_fabric().get_intent(pending.intent_id).status == IntentStatus.APPROVAL_REQUIRED


# ----- detail -----


def test_get_approval_detail(client: TestClient):
    pending = _seed_pending_intent()
    r = client.get(f"/cognition/approval/{pending.intent_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"]["intent_id"] == pending.intent_id
    assert body["decision"]["selected_plan"]["suppliers"][0]["supplier"] == "colombia-farm"


def test_get_approval_404(client: TestClient):
    r = client.get("/cognition/approval/no-such")
    assert r.status_code == 404


# ----- actions -----


def test_approve(client: TestClient):
    pending = _seed_pending_intent()
    r = client.post(f"/cognition/intent/{pending.intent_id}/approve")
    assert r.status_code == 200
    body = r.json()
    assert body["new_status"] == "approved"
    assert get_fabric().get_intent(pending.intent_id).status == IntentStatus.APPROVED


def test_reject(client: TestClient):
    pending = _seed_pending_intent()
    r = client.post(
        f"/cognition/intent/{pending.intent_id}/reject",
        json={"note": "weather too risky this week"},
    )
    assert r.status_code == 200
    assert r.json()["new_status"] == "rejected"
    assert r.json()["note"] == "weather too risky this week"
    assert get_fabric().get_intent(pending.intent_id).status == IntentStatus.REJECTED


def test_request_alternative_resets_to_grounding(client: TestClient):
    pending = _seed_pending_intent()
    r = client.post(f"/cognition/intent/{pending.intent_id}/request-alternative")
    assert r.status_code == 200
    assert r.json()["new_status"] == "grounding"
    assert get_fabric().get_intent(pending.intent_id).status == IntentStatus.GROUNDING


def test_action_on_unknown_intent_404(client: TestClient):
    r = client.post("/cognition/intent/missing/approve")
    assert r.status_code == 404


def test_action_idempotency_409_after_terminal(client: TestClient):
    pending = _seed_pending_intent()
    client.post(f"/cognition/intent/{pending.intent_id}/approve")
    r = client.post(f"/cognition/intent/{pending.intent_id}/reject")
    assert r.status_code == 409


def test_request_alternative_then_re_evaluates(client: TestClient):
    """After request-alternative, status returns to GROUNDING; a fresh inbox
    poll sees the same intent again because the decision still requires
    approval."""
    pending = _seed_pending_intent()
    client.get("/cognition/approvals")  # promote to APPROVAL_REQUIRED
    client.post(f"/cognition/intent/{pending.intent_id}/request-alternative")
    assert get_fabric().get_intent(pending.intent_id).status == IntentStatus.GROUNDING

    r = client.get("/cognition/approvals")
    body = r.json()
    # Still pending — same conditions, promoted again.
    assert any(item["intent"]["intent_id"] == pending.intent_id for item in body)

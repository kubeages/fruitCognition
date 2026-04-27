"""End-to-end engine pipeline + the new conflicts/options API endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cognition.api.router import create_cognition_router
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract
from cognition.services.cognition_fabric import get_fabric, reset_fabric
from cognition.services.engine_pipeline import EvaluatedOption, evaluate_intent


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


def _seed(intent: IntentContract, claims: list[Claim]) -> None:
    f = get_fabric()
    f.save_intent(intent)
    for c in claims:
        f.save_claim(c)


# ----- pure orchestrator -----


def test_evaluate_intent_missing_returns_none():
    assert evaluate_intent("does-not-exist") is None


def test_full_pipeline_one_supplier_within_budget():
    intent = IntentContract(
        goal="x", quantity_lb=200, max_price_usd=600, delivery_days=7,
        human_approval_required_if=["price_above_budget", "weather_risk_high"],
    )
    _seed(intent, [
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="inventory", subject="mango",
              value={"available_lb": 320, "origin": "colombia", "fruit_type": "mango"}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="price", subject="mango", value={"unit_price_usd": 2.0}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="quality", subject="mango", value={"quality_score": 0.92}),
        Claim(intent_id=intent.intent_id, agent_id="weather-mcp",
              claim_type="weather_risk", subject="colombia",
              value={"region": "colombia", "weather_risk_score": 0.1}),
    ])

    ev = evaluate_intent(intent.intent_id)
    assert ev is not None
    assert len(ev.options) == 1
    o = ev.options[0]
    assert isinstance(o, EvaluatedOption)
    assert o.supplier == "colombia-farm"
    assert o.total_price_usd == 400.0
    assert o.within_budget is True
    assert o.weather_risk_level == "low"
    assert o.allowed is True
    assert o.requires_human_approval is False
    # No conflicts when everything fits.
    assert ev.conflicts == []


def test_full_pipeline_high_weather_redeems_via_approval():
    intent = IntentContract(
        goal="x", quantity_lb=200, max_price_usd=1000, delivery_days=10,
        human_approval_required_if=["weather_risk_high"],
    )
    _seed(intent, [
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="inventory", subject="mango",
              value={"available_lb": 500, "origin": "colombia"}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="price", subject="mango", value={"unit_price_usd": 2.0}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="quality", subject="mango", value={"quality_score": 0.9}),
        Claim(intent_id=intent.intent_id, agent_id="weather-mcp",
              claim_type="weather_risk", subject="colombia",
              value={"region": "colombia", "weather_risk_score": 0.8, "forecast": "storms"}),
    ])

    ev = evaluate_intent(intent.intent_id)
    o = ev.options[0]
    assert o.weather_risk_level == "high"
    assert o.allowed is False
    assert o.requires_human_approval is True
    assert "weather_risk_high" in o.violations
    # Resolver also surfaces this as a conflict.
    assert any(c.conflict_type == "weather_risk_high" for c in ev.conflicts)


def test_options_sort_allowed_first_then_by_rank():
    intent = IntentContract(
        goal="x", quantity_lb=200, max_price_usd=10000,
        human_approval_required_if=["weather_risk_high"],
    )
    _seed(intent, [
        # Two suppliers, one allowed (low weather) one not (high weather).
        Claim(intent_id=intent.intent_id, agent_id="ok-farm",
              claim_type="inventory", subject="mango",
              value={"available_lb": 500, "origin": "colombia"}),
        Claim(intent_id=intent.intent_id, agent_id="ok-farm",
              claim_type="price", subject="mango", value={"unit_price_usd": 5.0}),
        Claim(intent_id=intent.intent_id, agent_id="ok-farm",
              claim_type="quality", subject="mango", value={"quality_score": 0.9}),
        Claim(intent_id=intent.intent_id, agent_id="risky-farm",
              claim_type="inventory", subject="mango",
              value={"available_lb": 500, "origin": "brazil"}),
        Claim(intent_id=intent.intent_id, agent_id="risky-farm",
              claim_type="price", subject="mango", value={"unit_price_usd": 1.0}),  # cheaper
        Claim(intent_id=intent.intent_id, agent_id="risky-farm",
              claim_type="quality", subject="mango", value={"quality_score": 0.9}),
        Claim(intent_id=intent.intent_id, agent_id="weather-mcp",
              claim_type="weather_risk", subject="brazil",
              value={"region": "brazil", "weather_risk_score": 0.8}),
        Claim(intent_id=intent.intent_id, agent_id="weather-mcp",
              claim_type="weather_risk", subject="colombia",
              value={"region": "colombia", "weather_risk_score": 0.1}),
    ])

    ev = evaluate_intent(intent.intent_id)
    suppliers = [o.supplier for o in ev.options]
    # ok-farm comes first because it's allowed, even though risky-farm has lower cost.
    assert suppliers == ["ok-farm", "risky-farm"]
    assert ev.options[0].allowed is True
    assert ev.options[1].allowed is False


# ----- HTTP endpoints -----


def test_conflicts_endpoint(client: TestClient):
    intent = IntentContract(
        goal="x", quantity_lb=500, max_price_usd=900, delivery_days=10,
    )
    _seed(intent, [
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="inventory", subject="mango",
              value={"available_lb": 200, "origin": "colombia"}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="price", subject="mango", value={"unit_price_usd": 2.5}),
    ])

    r = client.get(f"/cognition/intent/{intent.intent_id}/conflicts")
    assert r.status_code == 200
    types = sorted({c["conflict_type"] for c in r.json()})
    assert "insufficient_inventory" in types
    assert "price_above_budget" in types


def test_options_endpoint(client: TestClient):
    intent = IntentContract(goal="x", quantity_lb=200, max_price_usd=600)
    _seed(intent, [
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="inventory", subject="mango",
              value={"available_lb": 500, "origin": "colombia"}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="price", subject="mango", value={"unit_price_usd": 2.0}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="quality", subject="mango", value={"quality_score": 0.9}),
    ])

    r = client.get(f"/cognition/intent/{intent.intent_id}/options")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["supplier"] == "colombia-farm"
    assert body[0]["total_price_usd"] == 400.0
    assert body[0]["within_budget"] is True
    assert body[0]["allowed"] is True


def test_state_endpoint_includes_conflicts_and_options(client: TestClient):
    intent = IntentContract(goal="x", quantity_lb=200, max_price_usd=600)
    _seed(intent, [
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="inventory", subject="mango",
              value={"available_lb": 500, "origin": "colombia"}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="price", subject="mango", value={"unit_price_usd": 2.0}),
        Claim(intent_id=intent.intent_id, agent_id="colombia-farm",
              claim_type="quality", subject="mango", value={"quality_score": 0.9}),
    ])

    r = client.get(f"/cognition/intent/{intent.intent_id}/state")
    body = r.json()
    assert "conflicts" in body
    assert "options" in body
    assert len(body["options"]) == 1
    assert body["options"][0]["allowed"] is True


def test_404_on_unknown_intent_for_engine_endpoints(client: TestClient):
    assert client.get("/cognition/intent/nope/conflicts").status_code == 404
    assert client.get("/cognition/intent/nope/options").status_code == 404

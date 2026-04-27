"""Read-only /cognition/* endpoints."""

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


def _seed_intent(**overrides) -> IntentContract:
    intent = IntentContract(
        goal="fulfil_fruit_order",
        fruit_type=overrides.get("fruit_type", "mango"),
        quantity_lb=overrides.get("quantity_lb", 500.0),
        max_price_usd=overrides.get("max_price_usd", 1200.0),
        delivery_days=overrides.get("delivery_days", 7),
        status=overrides.get("status", IntentStatus.GROUNDING),
    )
    get_fabric().save_intent(intent)
    return intent


def _seed_claim(intent_id: str, claim_type: str = "inventory", **value) -> Claim:
    claim = Claim(
        intent_id=intent_id,
        agent_id="colombia-mango-farm",
        claim_type=claim_type,
        subject="mango",
        value=value or {"available_lb": 320},
    )
    get_fabric().save_claim(claim)
    return claim


def test_list_intents_empty(client: TestClient):
    r = client.get("/cognition/intents")
    assert r.status_code == 200
    assert r.json() == {"items": []}


def test_list_intents_returns_summaries(client: TestClient):
    a = _seed_intent(fruit_type="mango")
    b = _seed_intent(fruit_type="apple", quantity_lb=200.0)
    r = client.get("/cognition/intents")
    items = r.json()["items"]
    assert len(items) == 2
    by_id = {it["intent_id"]: it for it in items}
    assert by_id[a.intent_id]["fruit_type"] == "mango"
    assert by_id[a.intent_id]["status"] == "grounding"
    assert by_id[b.intent_id]["quantity_lb"] == 200.0


def test_get_intent_full_payload(client: TestClient):
    intent = _seed_intent()
    r = client.get(f"/cognition/intent/{intent.intent_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["intent_id"] == intent.intent_id
    assert body["fruit_type"] == "mango"
    assert body["max_price_usd"] == 1200.0
    assert body["status"] == "grounding"


def test_get_intent_404(client: TestClient):
    r = client.get("/cognition/intent/nope")
    assert r.status_code == 404
    assert "nope" in r.json()["detail"]


def test_list_claims_empty_returns_200_not_404(client: TestClient):
    intent = _seed_intent()
    r = client.get(f"/cognition/intent/{intent.intent_id}/claims")
    assert r.status_code == 200
    assert r.json() == []


def test_list_claims_for_unknown_intent_also_empty(client: TestClient):
    r = client.get("/cognition/intent/never-existed/claims")
    assert r.status_code == 200
    assert r.json() == []


def test_list_claims_returns_typed_payloads(client: TestClient):
    intent = _seed_intent()
    _seed_claim(intent.intent_id, "inventory", available_lb=320)
    _seed_claim(intent.intent_id, "price", unit_price_usd=2.1)
    _seed_claim(intent.intent_id, "quality", quality_score=0.92)

    r = client.get(f"/cognition/intent/{intent.intent_id}/claims")
    assert r.status_code == 200
    body = r.json()
    assert sorted(c["claim_type"] for c in body) == ["inventory", "price", "quality"]
    assert all(c["intent_id"] == intent.intent_id for c in body)


def test_get_state_combines_intent_and_claims(client: TestClient):
    intent = _seed_intent()
    _seed_claim(intent.intent_id, "inventory", available_lb=320)

    r = client.get(f"/cognition/intent/{intent.intent_id}/state")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"]["intent_id"] == intent.intent_id
    assert len(body["claims"]) == 1
    assert body["claims"][0]["claim_type"] == "inventory"


def test_get_state_404_for_unknown_intent(client: TestClient):
    r = client.get("/cognition/intent/nope/state")
    assert r.status_code == 404


def test_list_beliefs_empty_when_no_claims(client: TestClient):
    intent = _seed_intent()
    r = client.get(f"/cognition/intent/{intent.intent_id}/beliefs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_beliefs_rolls_up_supply_options(client: TestClient):
    intent = _seed_intent()
    _seed_claim(intent.intent_id, "inventory", available_lb=320, origin="colombia")
    _seed_claim(intent.intent_id, "price", unit_price_usd=2.1)
    _seed_claim(intent.intent_id, "quality", quality_score=0.92)

    r = client.get(f"/cognition/intent/{intent.intent_id}/beliefs")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    b = body[0]
    assert b["belief_type"] == "supply_option"
    assert b["agent_id"] == "colombia-mango-farm"
    assert b["value"]["available_lb"] == 320
    assert b["value"]["unit_price_usd"] == 2.1
    assert b["value"]["quality_score"] == 0.92


def test_state_includes_beliefs(client: TestClient):
    intent = _seed_intent()
    _seed_claim(intent.intent_id, "inventory", available_lb=320, origin="colombia")
    _seed_claim(intent.intent_id, "price", unit_price_usd=2.1)
    r = client.get(f"/cognition/intent/{intent.intent_id}/state")
    body = r.json()
    assert len(body["beliefs"]) == 1
    assert body["beliefs"][0]["belief_type"] == "supply_option"

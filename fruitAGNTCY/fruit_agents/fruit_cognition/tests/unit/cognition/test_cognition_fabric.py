import pytest

from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract
from cognition.services.cognition_fabric import (
    InMemoryCognitionFabric,
    get_fabric,
    reset_fabric,
)


@pytest.fixture
def fabric() -> InMemoryCognitionFabric:
    return InMemoryCognitionFabric()


@pytest.fixture(autouse=True)
def _clean_singleton():
    reset_fabric()
    yield
    reset_fabric()


def test_save_and_get_intent(fabric: InMemoryCognitionFabric):
    intent = IntentContract(goal="fulfil_fruit_order", fruit_type="mango")
    fabric.save_intent(intent)
    assert fabric.get_intent(intent.intent_id) == intent


def test_get_intent_missing_returns_none(fabric: InMemoryCognitionFabric):
    assert fabric.get_intent("does-not-exist") is None


def test_list_intents(fabric: InMemoryCognitionFabric):
    a = IntentContract(goal="fulfil_fruit_order", fruit_type="apple")
    b = IntentContract(goal="fulfil_fruit_order", fruit_type="banana")
    fabric.save_intent(a)
    fabric.save_intent(b)
    listed = fabric.list_intents()
    assert {i.intent_id for i in listed} == {a.intent_id, b.intent_id}


def test_save_intent_overwrites_same_id(fabric: InMemoryCognitionFabric):
    intent = IntentContract(goal="fulfil_fruit_order", fruit_type="mango")
    fabric.save_intent(intent)
    intent2 = intent.model_copy(update={"fruit_type": "apple"})
    fabric.save_intent(intent2)
    assert fabric.get_intent(intent.intent_id).fruit_type == "apple"


def _claim(intent_id: str, claim_type: str = "inventory") -> Claim:
    return Claim(
        intent_id=intent_id,
        agent_id="colombia-mango-farm",
        claim_type=claim_type,
        subject="mango",
        value={"available_lb": 100},
    )


def test_save_and_list_claims(fabric: InMemoryCognitionFabric):
    c1 = _claim("intent-1", "inventory")
    c2 = _claim("intent-1", "price")
    c3 = _claim("intent-2", "quality")
    fabric.save_claim(c1)
    fabric.save_claim(c2)
    fabric.save_claim(c3)
    assert [c.claim_type for c in fabric.list_claims("intent-1")] == ["inventory", "price"]
    assert [c.claim_type for c in fabric.list_claims("intent-2")] == ["quality"]
    assert fabric.list_claims("intent-unknown") == []


def test_list_claims_returns_copy(fabric: InMemoryCognitionFabric):
    fabric.save_claim(_claim("i"))
    snap = fabric.list_claims("i")
    snap.append(_claim("i", "price"))
    assert len(fabric.list_claims("i")) == 1


def test_get_fabric_returns_singleton():
    a = get_fabric()
    b = get_fabric()
    assert a is b


def test_reset_fabric_drops_singleton():
    a = get_fabric()
    a.save_intent(IntentContract(goal="x"))
    reset_fabric()
    b = get_fabric()
    assert b is not a
    assert b.list_intents() == []

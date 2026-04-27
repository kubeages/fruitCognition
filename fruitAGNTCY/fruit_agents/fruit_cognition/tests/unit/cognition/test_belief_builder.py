import pytest

from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.services.belief_builder import BeliefBuilder


@pytest.fixture
def builder() -> BeliefBuilder:
    return BeliefBuilder()


def _claim(agent_id: str, claim_type: str, subject: str = "mango", confidence: float = 1.0, **value) -> Claim:
    return Claim(
        intent_id="i1",
        agent_id=agent_id,
        claim_type=claim_type,
        subject=subject,
        value=value,
        confidence=confidence,
    )


def test_no_claims_no_beliefs(builder: BeliefBuilder):
    assert builder.build(intent_id="i1", claims=[]) == []


def test_supply_option_aggregates_one_supplier(builder: BeliefBuilder):
    claims = [
        _claim("colombia-farm", "inventory", available_lb=320, origin="colombia", fruit_type="mango"),
        _claim("colombia-farm", "price", unit_price_usd=2.1),
        _claim("colombia-farm", "quality", quality_score=0.92),
    ]
    beliefs = builder.build(intent_id="i1", claims=claims)
    assert len(beliefs) == 1
    b = beliefs[0]
    assert isinstance(b, Belief)
    assert b.belief_type == "supply_option"
    assert b.agent_id == "colombia-farm"
    assert b.subject == "mango"
    assert b.value == {
        "available_lb": 320,
        "origin": "colombia",
        "fruit_type": "mango",
        "unit_price_usd": 2.1,
        "quality_score": 0.92,
    }
    assert set(b.source_claim_ids) == {c.claim_id for c in claims}
    assert b.confidence == 1.0


def test_two_suppliers_two_beliefs(builder: BeliefBuilder):
    claims = [
        _claim("colombia-farm", "inventory", available_lb=320, origin="colombia"),
        _claim("colombia-farm", "price", unit_price_usd=2.1),
        _claim("brazil-farm", "inventory", available_lb=500, origin="brazil"),
        _claim("brazil-farm", "price", unit_price_usd=1.95),
    ]
    beliefs = builder.build(intent_id="i1", claims=claims)
    assert [b.agent_id for b in beliefs] == ["brazil-farm", "colombia-farm"]  # sorted
    co = next(b for b in beliefs if b.agent_id == "colombia-farm")
    assert co.value["available_lb"] == 320
    assert co.value["unit_price_usd"] == 2.1


def test_partial_claims_partial_belief_value(builder: BeliefBuilder):
    """Supplier with only inventory → belief still emitted, with what we know."""
    claims = [_claim("colombia-farm", "inventory", available_lb=320)]
    beliefs = builder.build(intent_id="i1", claims=claims)
    assert len(beliefs) == 1
    assert beliefs[0].value == {"available_lb": 320}
    assert "unit_price_usd" not in beliefs[0].value


def test_non_supply_claim_types_ignored(builder: BeliefBuilder):
    claims = [
        _claim("weather-mcp", "weather_risk", subject="colombia", weather_risk_score=0.3),
        _claim("colombia-farm", "inventory", available_lb=320),
    ]
    beliefs = builder.build(intent_id="i1", claims=claims)
    assert len(beliefs) == 1
    assert beliefs[0].agent_id == "colombia-farm"


def test_confidence_averaged(builder: BeliefBuilder):
    claims = [
        _claim("colombia-farm", "inventory", confidence=0.8, available_lb=100),
        _claim("colombia-farm", "price", confidence=0.6, unit_price_usd=2.0),
    ]
    beliefs = builder.build(intent_id="i1", claims=claims)
    assert beliefs[0].confidence == pytest.approx(0.7)


def test_origin_claim_only_still_belief(builder: BeliefBuilder):
    """A bare origin claim is enough to register a supply_option."""
    claims = [_claim("colombia-farm", "origin", origin="colombia")]
    beliefs = builder.build(intent_id="i1", claims=claims)
    assert len(beliefs) == 1
    assert beliefs[0].value == {"origin": "colombia"}

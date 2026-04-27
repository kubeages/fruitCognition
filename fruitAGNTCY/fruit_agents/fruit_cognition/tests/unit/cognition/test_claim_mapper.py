import pytest

from cognition.schemas.claim import Claim
from cognition.schemas.evidence import evidence_ref
from cognition.services.claim_mapper import ClaimMapper


@pytest.fixture
def mapper() -> ClaimMapper:
    return ClaimMapper()


# ----- evidence_ref helper -----


def test_evidence_ref_with_explicit_id():
    assert evidence_ref("inventory", "colombia-mango-farm", "2026-04-27") == (
        "inventory:colombia-mango-farm:2026-04-27"
    )


def test_evidence_ref_default_id_is_iso_timestamp():
    ref = evidence_ref("weather", "weather-mcp")
    parts = ref.split(":", 2)
    assert parts[0] == "weather"
    assert parts[1] == "weather-mcp"
    # Third part is an ISO 8601 timestamp; just check it parses as one
    from datetime import datetime
    datetime.fromisoformat(parts[2])


# ----- farm responses -----


def test_farm_full_response_fans_out_to_four_claims(mapper: ClaimMapper):
    claims = mapper.map_farm_response(
        intent_id="fruit-intent-abc",
        agent_id="colombia-mango-farm",
        response={
            "fruit_type": "mango",
            "available_lb": 320,
            "unit_price_usd": 2.1,
            "quality_score": 0.92,
            "origin": "colombia",
            "confidence": 0.91,
        },
    )
    types = sorted(c.claim_type for c in claims)
    assert types == ["inventory", "origin", "price", "quality"]
    for c in claims:
        assert isinstance(c, Claim)
        assert c.intent_id == "fruit-intent-abc"
        assert c.agent_id == "colombia-mango-farm"
        assert c.subject == "mango"
        assert c.confidence == pytest.approx(0.91)
        assert c.evidence_refs and c.evidence_refs[0].startswith("farm:colombia-mango-farm:")


def test_farm_partial_response_skips_missing_fields(mapper: ClaimMapper):
    claims = mapper.map_farm_response(
        intent_id="i", agent_id="a",
        response={"fruit_type": "apple", "available_lb": 100},
    )
    assert [c.claim_type for c in claims] == ["inventory"]
    assert claims[0].value == {"available_lb": 100, "origin": None, "fruit_type": "apple"}


def test_farm_empty_response_no_claims(mapper: ClaimMapper):
    assert mapper.map_farm_response(intent_id="i", agent_id="a", response={}) == []


# ----- weather responses -----


def test_weather_response_one_claim(mapper: ClaimMapper):
    claims = mapper.map_weather_response(
        intent_id="i", agent_id="weather-mcp",
        response={
            "region": "colombia",
            "weather_risk_score": 0.3,
            "horizon_days": 7,
            "forecast": "partly cloudy",
        },
    )
    assert len(claims) == 1
    c = claims[0]
    assert c.claim_type == "weather_risk"
    assert c.subject == "colombia"
    assert c.value == {
        "weather_risk_score": 0.3,
        "forecast": "partly cloudy",
        "region": "colombia",
        "horizon_days": 7,
    }


def test_weather_response_no_score_no_claim(mapper: ClaimMapper):
    assert mapper.map_weather_response(
        intent_id="i", agent_id="a",
        response={"region": "anywhere"},
    ) == []


# ----- logistics responses -----


def test_logistics_full_response_three_claims(mapper: ClaimMapper):
    claims = mapper.map_logistics_response(
        intent_id="i", agent_id="shipper",
        response={
            "route": "colombia-eu",
            "capacity_lb": 5000,
            "shipping_cost_usd": 850,
            "eta_days": 6,
            "carrier": "AcmeCargo",
        },
    )
    types = sorted(c.claim_type for c in claims)
    assert types == ["delivery_sla", "shipping_capacity", "shipping_cost"]
    sla_claim = next(c for c in claims if c.claim_type == "delivery_sla")
    assert sla_claim.value == {"eta_days": 6, "carrier": "AcmeCargo"}


def test_logistics_only_sla_via_sla_days(mapper: ClaimMapper):
    claims = mapper.map_logistics_response(
        intent_id="i", agent_id="shipper",
        response={"sla_days": 5},
    )
    assert [c.claim_type for c in claims] == ["delivery_sla"]
    assert claims[0].value == {"sla_days": 5}


# ----- payment responses -----


def test_payment_response(mapper: ClaimMapper):
    claims = mapper.map_payment_response(
        intent_id="i", agent_id="accountant",
        response={"status": "paid", "amount_usd": 1200, "order_id": "ord-42"},
    )
    assert len(claims) == 1
    c = claims[0]
    assert c.claim_type == "payment_status"
    assert c.subject == "ord-42"
    assert c.value == {"status": "paid", "amount_usd": 1200, "order_id": "ord-42"}


def test_payment_no_status_no_claim(mapper: ClaimMapper):
    assert mapper.map_payment_response(intent_id="i", agent_id="a", response={}) == []

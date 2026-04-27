import pytest

from cognition.engines.cost_engine import CostEvaluation
from cognition.engines.policy_guardrail_engine import (
    GuardrailVerdict,
    PolicyGuardrailEngine,
)
from cognition.engines.weather_risk_engine import WeatherRiskEvaluation
from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


@pytest.fixture
def engine() -> PolicyGuardrailEngine:
    return PolicyGuardrailEngine()


def _intent(**overrides) -> IntentContract:
    return IntentContract(
        goal="x",
        quantity_lb=overrides.get("quantity_lb", 500.0),
        max_price_usd=overrides.get("max_price_usd", 1200.0),
        delivery_days=overrides.get("delivery_days", 7),
        hard_constraints=overrides.get("hard_constraints", {}),
        human_approval_required_if=overrides.get(
            "human_approval_required_if",
            ["price_above_budget", "weather_risk_high", "delivery_sla_at_risk"],
        ),
    )


def _supply(agent: str, **value) -> Belief:
    return Belief(
        intent_id="i", belief_type="supply_option", subject="mango",
        agent_id=agent, value=value,
    )


def _cost(supplier: str, *, within: bool | None = True, total: float | None = 500.0):
    return CostEvaluation(
        supplier=supplier, subject="mango", available_lb=600,
        unit_price_usd=2.0, fulfilled_lb=500, total_price_usd=total,
        within_budget=within, rank=1,
    )


def _weather(supplier: str, level: str = "low"):
    return WeatherRiskEvaluation(supplier=supplier, origin="colombia", risk_level=level)


def test_no_violations_allowed(engine: PolicyGuardrailEngine):
    intent = _intent()
    beliefs = [_supply("colombia-farm", quality_score=0.9)]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("colombia-farm")], weather=[_weather("colombia-farm")],
    )
    assert len(verdicts) == 1
    v = verdicts[0]
    assert isinstance(v, GuardrailVerdict)
    assert v.allowed is True
    assert v.requires_human_approval is False
    assert v.violations == []


def test_price_above_budget_redeemable_when_listed(engine: PolicyGuardrailEngine):
    intent = _intent(human_approval_required_if=["price_above_budget"])
    beliefs = [_supply("colombia-farm", quality_score=0.9)]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("colombia-farm", within=False, total=1500)],
        weather=[_weather("colombia-farm")],
    )
    v = verdicts[0]
    assert v.allowed is False
    assert v.requires_human_approval is True
    assert v.violations == ["price_above_budget"]
    assert "price_above_budget" in v.rationale


def test_price_above_budget_hard_blocked_when_not_listed(engine: PolicyGuardrailEngine):
    intent = _intent(human_approval_required_if=[])  # nothing redeemable
    beliefs = [_supply("colombia-farm", quality_score=0.9)]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("colombia-farm", within=False)],
        weather=[_weather("colombia-farm")],
    )
    v = verdicts[0]
    assert v.allowed is False
    assert v.requires_human_approval is False
    assert "Hard-blocked" in v.rationale


def test_weather_high_redeemable(engine: PolicyGuardrailEngine):
    intent = _intent()
    beliefs = [_supply("colombia-farm", quality_score=0.9)]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("colombia-farm")],
        weather=[_weather("colombia-farm", level="high")],
    )
    v = verdicts[0]
    assert v.violations == ["weather_risk_high"]
    assert v.requires_human_approval is True


def test_delivery_sla_violation_from_claim(engine: PolicyGuardrailEngine):
    intent = _intent(delivery_days=5)
    beliefs = [_supply("colombia-farm", quality_score=0.9)]
    claims = [Claim(
        intent_id="i", agent_id="colombia-farm", claim_type="delivery_sla",
        subject="mango", value={"eta_days": 9},
    )]
    verdicts = engine.evaluate(
        intent=intent, claims=claims, beliefs=beliefs,
        cost=[_cost("colombia-farm")], weather=[_weather("colombia-farm")],
    )
    v = verdicts[0]
    assert "delivery_sla_at_risk" in v.violations
    assert v.requires_human_approval is True


def test_quality_below_threshold_is_hard_block(engine: PolicyGuardrailEngine):
    intent = _intent()  # quality not in human_approval_required_if
    beliefs = [_supply("low-q-farm", quality_score=0.3)]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("low-q-farm")], weather=[_weather("low-q-farm")],
    )
    v = verdicts[0]
    assert v.violations == ["quality_below_threshold"]
    assert v.allowed is False
    assert v.requires_human_approval is False


def test_quality_threshold_overridable_via_intent(engine: PolicyGuardrailEngine):
    intent = _intent(hard_constraints={"min_quality_score": 0.95})
    beliefs = [_supply("good-farm", quality_score=0.9)]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("good-farm")], weather=[_weather("good-farm")],
    )
    assert "quality_below_threshold" in verdicts[0].violations


def test_multiple_violations_mixed_redeemability(engine: PolicyGuardrailEngine):
    intent = _intent(human_approval_required_if=["price_above_budget"])
    # quality is hard-block; price is redeemable -> hard-block wins.
    beliefs = [_supply("mixed-farm", quality_score=0.3)]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("mixed-farm", within=False)],
        weather=[_weather("mixed-farm")],
    )
    v = verdicts[0]
    assert set(v.violations) == {"price_above_budget", "quality_below_threshold"}
    assert v.allowed is False
    assert v.requires_human_approval is False  # hard-block wins
    assert "quality_below_threshold" in v.rationale


def test_per_supplier_verdicts_sorted(engine: PolicyGuardrailEngine):
    intent = _intent()
    beliefs = [
        _supply("colombia-farm", quality_score=0.9),
        _supply("brazil-farm", quality_score=0.9),
    ]
    verdicts = engine.evaluate(
        intent=intent, claims=[], beliefs=beliefs,
        cost=[_cost("colombia-farm"), _cost("brazil-farm")],
        weather=[_weather("colombia-farm"), _weather("brazil-farm")],
    )
    assert [v.supplier for v in verdicts] == ["brazil-farm", "colombia-farm"]

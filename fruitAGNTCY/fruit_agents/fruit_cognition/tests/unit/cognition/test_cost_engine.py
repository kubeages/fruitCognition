import pytest

from cognition.engines.cost_engine import CostEngine, CostEvaluation
from cognition.schemas.belief import Belief
from cognition.schemas.intent_contract import IntentContract


@pytest.fixture
def engine() -> CostEngine:
    return CostEngine()


def _intent(**overrides) -> IntentContract:
    return IntentContract(
        goal="x",
        quantity_lb=overrides.get("quantity_lb", 500.0),
        max_price_usd=overrides.get("max_price_usd", 1200.0),
    )


def _supply(agent: str, **value) -> Belief:
    return Belief(
        intent_id="i", belief_type="supply_option", subject="mango",
        agent_id=agent, value=value,
    )


def test_no_supply_options_returns_empty(engine: CostEngine):
    assert engine.evaluate(intent=_intent(), beliefs=[]) == []


def test_single_supplier_within_budget(engine: CostEngine):
    options = engine.evaluate(
        intent=_intent(quantity_lb=200, max_price_usd=1000),
        beliefs=[_supply("colombia", available_lb=300, unit_price_usd=2.5)],
    )
    assert len(options) == 1
    o = options[0]
    assert isinstance(o, CostEvaluation)
    assert o.supplier == "colombia"
    assert o.fulfilled_lb == 200  # min(300, 200)
    assert o.total_price_usd == 500.0
    assert o.within_budget is True
    assert o.rank == 1


def test_supplier_short_on_inventory_uses_available(engine: CostEngine):
    options = engine.evaluate(
        intent=_intent(quantity_lb=500, max_price_usd=1000),
        beliefs=[_supply("colombia", available_lb=320, unit_price_usd=2.0)],
    )
    o = options[0]
    assert o.fulfilled_lb == 320  # capped by availability
    assert o.total_price_usd == 640.0
    assert o.within_budget is True


def test_above_budget_marked(engine: CostEngine):
    options = engine.evaluate(
        intent=_intent(quantity_lb=500, max_price_usd=900),
        beliefs=[_supply("colombia", available_lb=600, unit_price_usd=2.5)],
    )
    o = options[0]
    assert o.total_price_usd == 1250.0
    assert o.within_budget is False


def test_ranking_ascending_by_total(engine: CostEngine):
    options = engine.evaluate(
        intent=_intent(quantity_lb=100),
        beliefs=[
            _supply("expensive", available_lb=200, unit_price_usd=5.0),  # 500
            _supply("cheap",     available_lb=200, unit_price_usd=1.0),  # 100
            _supply("medium",    available_lb=200, unit_price_usd=2.5),  # 250
        ],
    )
    assert [o.supplier for o in options] == ["cheap", "medium", "expensive"]
    assert [o.rank for o in options] == [1, 2, 3]


def test_unpriced_supplier_sinks_to_bottom(engine: CostEngine):
    options = engine.evaluate(
        intent=_intent(quantity_lb=100),
        beliefs=[
            _supply("nopricer", available_lb=200),  # no unit_price
            _supply("priced",   available_lb=200, unit_price_usd=2.0),
        ],
    )
    assert [o.supplier for o in options] == ["priced", "nopricer"]
    assert options[1].total_price_usd is None
    assert options[1].within_budget is None


def test_no_quantity_falls_back_to_available_lb(engine: CostEngine):
    intent = IntentContract(goal="x")  # no quantity
    options = CostEngine().evaluate(
        intent=intent,
        beliefs=[_supply("colombia", available_lb=300, unit_price_usd=2.0)],
    )
    o = options[0]
    assert o.fulfilled_lb == 300
    assert o.total_price_usd == 600.0
    assert o.within_budget is None  # no budget set


def test_non_supply_option_beliefs_ignored(engine: CostEngine):
    other = Belief(
        intent_id="i", belief_type="risk_outlook", subject="x",
        agent_id="weather", value={"unit_price_usd": 999},
    )
    options = engine.evaluate(intent=_intent(), beliefs=[other])
    assert options == []

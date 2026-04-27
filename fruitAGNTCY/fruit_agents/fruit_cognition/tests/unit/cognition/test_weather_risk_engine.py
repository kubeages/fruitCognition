import pytest

from cognition.engines.weather_risk_engine import WeatherRiskEngine
from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


@pytest.fixture
def engine() -> WeatherRiskEngine:
    return WeatherRiskEngine()


def _intent() -> IntentContract:
    return IntentContract(goal="x", quantity_lb=500.0)


def _supply(agent: str, origin: str | None) -> Belief:
    return Belief(
        intent_id="i", belief_type="supply_option", subject="mango",
        agent_id=agent, value={"origin": origin} if origin else {},
    )


def _weather(region: str, score: float | None, forecast: str | None = None) -> Claim:
    value = {"region": region}
    if score is not None:
        value["weather_risk_score"] = score
    if forecast is not None:
        value["forecast"] = forecast
    return Claim(
        intent_id="i", agent_id="weather-mcp", claim_type="weather_risk",
        subject=region, value=value,
    )


def test_no_supply_options_returns_empty(engine: WeatherRiskEngine):
    assert engine.evaluate(intent=_intent(), claims=[], beliefs=[]) == []


def test_no_matching_weather_claim_yields_unknown(engine: WeatherRiskEngine):
    evals = engine.evaluate(
        intent=_intent(),
        claims=[],
        beliefs=[_supply("colombia-farm", "colombia")],
    )
    assert len(evals) == 1
    assert evals[0].risk_level == "unknown"
    assert evals[0].score is None


@pytest.mark.parametrize(
    "score,level",
    [
        (0.05, "low"),
        (0.29, "low"),
        (0.30, "medium"),
        (0.55, "medium"),
        (0.60, "high"),
        (0.95, "high"),
    ],
)
def test_score_to_level_thresholds(engine: WeatherRiskEngine, score, level):
    evals = engine.evaluate(
        intent=_intent(),
        claims=[_weather("colombia", score)],
        beliefs=[_supply("colombia-farm", "colombia")],
    )
    assert evals[0].risk_level == level
    assert evals[0].score == score


def test_worst_score_wins_when_multiple_claims(engine: WeatherRiskEngine):
    evals = engine.evaluate(
        intent=_intent(),
        claims=[
            _weather("colombia", 0.1),
            _weather("colombia", 0.7, forecast="storms"),
            _weather("colombia", 0.4),
        ],
        beliefs=[_supply("colombia-farm", "colombia")],
    )
    e = evals[0]
    assert e.risk_level == "high"
    assert e.score == 0.7
    assert e.reason and "storms" in e.reason


def test_origin_match_is_case_insensitive(engine: WeatherRiskEngine):
    evals = engine.evaluate(
        intent=_intent(),
        claims=[_weather("Colombia", 0.5)],
        beliefs=[_supply("colombia-farm", "COLOMBIA")],
    )
    assert evals[0].risk_level == "medium"


def test_supplier_without_origin_yields_unknown(engine: WeatherRiskEngine):
    evals = engine.evaluate(
        intent=_intent(),
        claims=[_weather("colombia", 0.8)],
        beliefs=[_supply("mystery-farm", None)],
    )
    assert evals[0].risk_level == "unknown"
    assert evals[0].origin is None


def test_results_sorted_by_supplier(engine: WeatherRiskEngine):
    evals = engine.evaluate(
        intent=_intent(),
        claims=[_weather("colombia", 0.4), _weather("brazil", 0.2)],
        beliefs=[
            _supply("colombia-farm", "colombia"),
            _supply("brazil-farm", "brazil"),
        ],
    )
    assert [e.supplier for e in evals] == ["brazil-farm", "colombia-farm"]


def test_non_supply_beliefs_ignored(engine: WeatherRiskEngine):
    other = Belief(
        intent_id="i", belief_type="risk_outlook", subject="x",
        agent_id="weather", value={"origin": "colombia"},
    )
    evals = engine.evaluate(
        intent=_intent(),
        claims=[_weather("colombia", 0.5)],
        beliefs=[other],
    )
    assert evals == []

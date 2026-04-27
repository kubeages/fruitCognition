import pytest

from cognition.schemas.intent_contract import IntentStatus
from cognition.services.intent_manager import IntentManager


@pytest.fixture
def manager() -> IntentManager:
    return IntentManager()


def test_full_prompt_extraction(manager: IntentManager):
    intent = manager.create_from_prompt(
        "I need 500 lb of premium mango delivered within 7 days under $1,200. "
        "Prefer low weather risk and low-carbon shipping."
    )
    assert intent.intent_id.startswith("fruit-intent-")
    assert intent.goal == "fulfil_fruit_order"
    assert intent.fruit_type == "mango"
    assert intent.quantity_lb == 500.0
    assert intent.max_price_usd == 1200.0
    assert intent.delivery_days == 7
    assert intent.hard_constraints == {"delivery_days": 7, "max_price_usd": 1200.0}
    assert intent.soft_constraints == {
        "prefer_low_weather_risk": True,
        "prefer_low_carbon_shipping": True,
    }
    assert intent.human_approval_required_if == [
        "price_above_budget",
        "weather_risk_high",
        "delivery_sla_at_risk",
    ]
    assert intent.status is IntentStatus.DRAFT


def test_minimal_prompt_no_fields(manager: IntentManager):
    intent = manager.create_from_prompt("get me some fruit")
    assert intent.fruit_type is None
    assert intent.quantity_lb is None
    assert intent.max_price_usd is None
    assert intent.delivery_days is None
    assert intent.hard_constraints == {}
    assert intent.soft_constraints == {
        "prefer_low_weather_risk": False,
        "prefer_low_carbon_shipping": False,
    }


@pytest.mark.parametrize(
    "prompt,fruit",
    [
        ("apples please", "apple"),
        ("BANANAS for breakfast", "banana"),
        ("strawberry haul", "strawberry"),
        ("mango shipment", "mango"),
        ("kiwi order", None),  # not in vocabulary
    ],
)
def test_fruit_type_extraction(manager: IntentManager, prompt: str, fruit: str | None):
    assert manager.create_from_prompt(prompt).fruit_type == fruit


@pytest.mark.parametrize(
    "prompt,qty",
    [
        ("100 lb of bananas", 100.0),
        ("Order 2500 pounds", 2500.0),
        ("buy 12.5 lbs", 12.5),
        ("no quantity here", None),
    ],
)
def test_quantity_extraction(manager: IntentManager, prompt: str, qty: float | None):
    assert manager.create_from_prompt(prompt).quantity_lb == qty


@pytest.mark.parametrize(
    "prompt,price",
    [
        ("under $1,200", 1200.0),
        ("max 850 dollars", 850.0),
        ("budget $4,750.50", 4750.5),
        ("spend whatever", None),
    ],
)
def test_price_extraction(manager: IntentManager, prompt: str, price: float | None):
    assert manager.create_from_prompt(prompt).max_price_usd == price


@pytest.mark.parametrize(
    "prompt,days",
    [
        ("within 14 days", 14),
        ("within 1 day", 1),
        ("any time", None),
    ],
)
def test_delivery_days_extraction(manager: IntentManager, prompt: str, days: int | None):
    assert manager.create_from_prompt(prompt).delivery_days == days

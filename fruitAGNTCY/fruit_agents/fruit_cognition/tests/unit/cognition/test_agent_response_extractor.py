import pytest

from cognition.services.agent_response_extractor import (
    extract_farm_text,
    extract_logistics_text,
    extraction_enabled,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, True),
        ("true", True),
        ("True", True),
        ("on", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("off", False),
    ],
)
def test_extraction_enabled(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("COGNITION_CLAIM_EXTRACTION", raising=False)
    else:
        monkeypatch.setenv("COGNITION_CLAIM_EXTRACTION", value)
    assert extraction_enabled() is expected


def test_farm_text_full_response():
    text = (
        "Colombia mango farm reports 320 lbs available this week at $2.10 per lb. "
        "Quality is 92% (premium grade)."
    )
    out = extract_farm_text(text)
    assert out["fruit_type"] == "mango"
    assert out["available_lb"] == 320.0
    assert out["unit_price_usd"] == 2.10
    assert out["quality_score"] == 0.92
    assert out["origin"] == "colombia"


def test_farm_text_decimal_quality_score():
    out = extract_farm_text("Brazil banana yield is 5000 lbs at $0.85. Quality score 0.88.")
    assert out["quality_score"] == 0.88
    assert out["origin"] == "brazil"
    assert out["fruit_type"] == "banana"


def test_farm_text_default_origin_overrides_text_match():
    out = extract_farm_text("we have 100 lbs apples at $1.50", default_origin="brazil")
    assert out["origin"] == "brazil"


def test_farm_text_partial_response():
    out = extract_farm_text("strawberry shipment ready, 750 lbs total")
    assert out["available_lb"] == 750.0
    assert out["fruit_type"] == "strawberry"
    assert "unit_price_usd" not in out
    assert "quality_score" not in out


def test_farm_text_nothing_extractable_returns_empty():
    assert extract_farm_text("we'll get back to you") == {}


def test_logistics_text_full():
    out = extract_logistics_text(
        "Shipping cost is $850 with ETA 6 days from Colombia to EU port."
    )
    assert out["shipping_cost_usd"] == 850.0
    assert out["eta_days"] == 6


@pytest.mark.parametrize(
    "phrase,days",
    [
        ("delivered in 4 days", 4),
        ("delivery in 12 days", 12),
        ("within 3 days", 3),
    ],
)
def test_logistics_eta_phrasings(phrase, days):
    out = extract_logistics_text(f"Order accepted; {phrase}.")
    assert out["eta_days"] == days


def test_logistics_text_nothing_extractable():
    assert extract_logistics_text("we received your request") == {}

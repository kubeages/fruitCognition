from __future__ import annotations

import re

from cognition.schemas.intent_contract import IntentContract


_FRUIT_TYPES = ("mango", "apple", "banana", "strawberry")
_QUANTITY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds)\b", re.IGNORECASE)
_PRICE_RE = re.compile(
    r"(?:under|max|maximum|budget)\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)",
    re.IGNORECASE,
)
_DELIVERY_RE = re.compile(r"within\s+(\d+)\s+days?\b", re.IGNORECASE)


class IntentManager:
    """Convert a freeform user prompt into a structured IntentContract.

    Heuristic / regex-based for now; LLM-driven extraction is a future
    enhancement (see SPEC.md iter 2 implementation notes).
    """

    def create_from_prompt(self, prompt: str) -> IntentContract:
        fruit_type = self._extract_fruit_type(prompt)
        quantity_lb = self._extract_quantity_lb(prompt)
        max_price_usd = self._extract_max_price_usd(prompt)
        delivery_days = self._extract_delivery_days(prompt)

        hard_constraints: dict[str, object] = {}
        if delivery_days is not None:
            hard_constraints["delivery_days"] = delivery_days
        if max_price_usd is not None:
            hard_constraints["max_price_usd"] = max_price_usd

        lowered = prompt.lower()
        soft_constraints = {
            "prefer_low_weather_risk": "weather" in lowered,
            "prefer_low_carbon_shipping": "carbon" in lowered,
        }

        return IntentContract(
            goal="fulfil_fruit_order",
            fruit_type=fruit_type,
            quantity_lb=quantity_lb,
            max_price_usd=max_price_usd,
            delivery_days=delivery_days,
            hard_constraints=hard_constraints,
            soft_constraints=soft_constraints,
            human_approval_required_if=[
                "price_above_budget",
                "weather_risk_high",
                "delivery_sla_at_risk",
            ],
        )

    @staticmethod
    def _extract_fruit_type(prompt: str) -> str | None:
        lowered = prompt.lower()
        for fruit in _FRUIT_TYPES:
            if fruit in lowered:
                return fruit
        return None

    @staticmethod
    def _extract_quantity_lb(prompt: str) -> float | None:
        match = _QUANTITY_RE.search(prompt)
        return float(match.group(1)) if match else None

    @staticmethod
    def _extract_max_price_usd(prompt: str) -> float | None:
        match = _PRICE_RE.search(prompt)
        if not match:
            return None
        return float(match.group(1).replace(",", ""))

    @staticmethod
    def _extract_delivery_days(prompt: str) -> int | None:
        match = _DELIVERY_RE.search(prompt)
        return int(match.group(1)) if match else None

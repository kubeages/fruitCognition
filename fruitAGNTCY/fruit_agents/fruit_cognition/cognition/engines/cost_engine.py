"""Cost engine: rank supply_option beliefs by total price and mark
budget compliance.

Pure function over (intent, beliefs). Output rows are sorted ascending
by total price; rows with no price information sink to the bottom.
"""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel

from cognition.schemas.belief import Belief
from cognition.schemas.intent_contract import IntentContract


class CostEvaluation(BaseModel):
    supplier: str  # agent_id of the supply_option
    subject: str
    available_lb: float | None = None
    unit_price_usd: float | None = None
    # Quantity used for the cost calculation: min(intent.quantity_lb, available_lb).
    fulfilled_lb: float | None = None
    total_price_usd: float | None = None
    within_budget: bool | None = None
    rank: int  # 1-based; ties broken by supplier name


class CostEngine:
    def evaluate(
        self,
        *,
        intent: IntentContract,
        beliefs: Iterable[Belief],
    ) -> list[CostEvaluation]:
        options: list[CostEvaluation] = []
        for b in beliefs:
            if b.belief_type != "supply_option":
                continue
            unit = b.value.get("unit_price_usd")
            avail = b.value.get("available_lb")
            fulfilled: float | None = None
            total: float | None = None

            if intent.quantity_lb is not None:
                if avail is not None:
                    fulfilled = float(min(float(avail), float(intent.quantity_lb)))
                else:
                    fulfilled = float(intent.quantity_lb)
            elif avail is not None:
                fulfilled = float(avail)

            if unit is not None and fulfilled is not None:
                total = round(float(unit) * fulfilled, 2)

            within: bool | None = None
            if total is not None and intent.max_price_usd is not None:
                within = total <= float(intent.max_price_usd)

            options.append(
                CostEvaluation(
                    supplier=b.agent_id,
                    subject=b.subject,
                    available_lb=float(avail) if avail is not None else None,
                    unit_price_usd=float(unit) if unit is not None else None,
                    fulfilled_lb=fulfilled,
                    total_price_usd=total,
                    within_budget=within,
                    rank=0,  # filled in below
                )
            )

        # Sort: priced options ascending by total_price; un-priced at the tail.
        # Ties broken by supplier name for stable test output.
        def _key(o: CostEvaluation) -> tuple[int, float, str]:
            if o.total_price_usd is None:
                return (1, 0.0, o.supplier)
            return (0, o.total_price_usd, o.supplier)

        options.sort(key=_key)
        for i, o in enumerate(options, start=1):
            o.rank = i
        return options

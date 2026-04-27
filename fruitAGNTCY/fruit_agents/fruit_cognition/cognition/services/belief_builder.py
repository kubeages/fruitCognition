"""Aggregate Claims into typed Beliefs.

Iter 8 ships one builder pattern: ``supply_option`` rolls up the
inventory + price + quality + origin claims a single supplier reported
about a single subject (typically a fruit) into one decidable option.

Future iterations can add more belief types (e.g. ``logistics_option``
combining shipping_capacity + shipping_cost + delivery_sla; or
``risk_outlook`` from weather_risk + delivery_sla). The Builder is
stateless and pure — given the same claims, it returns the same beliefs.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim


SUPPLY_OPTION_CLAIM_TYPES = frozenset({"inventory", "price", "quality", "origin"})


class BeliefBuilder:
    """Pure aggregator from a list of Claims to a list of Beliefs."""

    def build(self, *, intent_id: str, claims: list[Claim]) -> list[Belief]:
        """Build all known belief types from the given claims.

        Currently emits only ``supply_option`` beliefs.
        """
        return self.build_supply_options(intent_id=intent_id, claims=claims)

    def build_supply_options(
        self, *, intent_id: str, claims: list[Claim]
    ) -> list[Belief]:
        # Group claims by (subject, agent_id). One belief per group.
        groups: dict[tuple[str, str], list[Claim]] = defaultdict(list)
        for c in claims:
            if c.claim_type not in SUPPLY_OPTION_CLAIM_TYPES:
                continue
            groups[(c.subject, c.agent_id)].append(c)

        beliefs: list[Belief] = []
        for (subject, agent_id), group in groups.items():
            value: dict[str, Any] = {}
            for c in group:
                if c.claim_type == "inventory":
                    value.setdefault("available_lb", c.value.get("available_lb"))
                    if value.get("origin") is None and c.value.get("origin") is not None:
                        value["origin"] = c.value.get("origin")
                    if value.get("fruit_type") is None and c.value.get("fruit_type") is not None:
                        value["fruit_type"] = c.value.get("fruit_type")
                elif c.claim_type == "price":
                    value.setdefault("unit_price_usd", c.value.get("unit_price_usd"))
                elif c.claim_type == "quality":
                    value.setdefault("quality_score", c.value.get("quality_score"))
                elif c.claim_type == "origin":
                    value.setdefault("origin", c.value.get("origin"))

            # Drop keys whose values are still None so the response is tidy.
            value = {k: v for k, v in value.items() if v is not None}

            confidence = sum(c.confidence for c in group) / len(group)
            beliefs.append(
                Belief(
                    intent_id=intent_id,
                    belief_type="supply_option",
                    subject=subject,
                    agent_id=agent_id,
                    value=value,
                    confidence=round(confidence, 4),
                    source_claim_ids=[c.claim_id for c in group],
                )
            )

        # Stable ordering for deterministic tests / UI: by agent then subject.
        beliefs.sort(key=lambda b: (b.agent_id, b.subject))
        return beliefs

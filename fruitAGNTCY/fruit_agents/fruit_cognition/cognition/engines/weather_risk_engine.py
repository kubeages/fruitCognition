"""Weather risk engine: assign a low/medium/high/unknown risk level to
each supply_option based on weather_risk claims that match the supplier's
origin.

Pure function over (intent, claims, beliefs).
"""

from __future__ import annotations

from typing import Iterable, Literal

from pydantic import BaseModel

from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


RiskLevel = Literal["low", "medium", "high", "unknown"]

# Score thresholds. Tunable via intent.soft_constraints if a future
# iteration wants per-intent overrides.
_MEDIUM_THRESHOLD = 0.30
_HIGH_THRESHOLD = 0.60


def _level_for_score(score: float | None) -> RiskLevel:
    if score is None:
        return "unknown"
    if score >= _HIGH_THRESHOLD:
        return "high"
    if score >= _MEDIUM_THRESHOLD:
        return "medium"
    return "low"


class WeatherRiskEvaluation(BaseModel):
    supplier: str  # supply_option agent_id
    origin: str | None
    risk_level: RiskLevel
    score: float | None = None
    reason: str | None = None
    source_claim_ids: list[str] = []


class WeatherRiskEngine:
    def evaluate(
        self,
        *,
        intent: IntentContract,
        claims: Iterable[Claim],
        beliefs: Iterable[Belief],
    ) -> list[WeatherRiskEvaluation]:
        weather_by_region: dict[str, list[Claim]] = {}
        for c in claims:
            if c.claim_type != "weather_risk":
                continue
            region = (c.value.get("region") or c.subject or "").lower()
            if not region:
                continue
            weather_by_region.setdefault(region, []).append(c)

        out: list[WeatherRiskEvaluation] = []
        for b in beliefs:
            if b.belief_type != "supply_option":
                continue
            origin = b.value.get("origin")
            origin_l = origin.lower() if isinstance(origin, str) else None

            matches = weather_by_region.get(origin_l, []) if origin_l else []
            if not matches:
                out.append(
                    WeatherRiskEvaluation(
                        supplier=b.agent_id,
                        origin=origin,
                        risk_level="unknown",
                    )
                )
                continue

            # Worst-case: take the highest score among matching weather claims.
            worst = max(
                (m for m in matches if m.value.get("weather_risk_score") is not None),
                key=lambda m: float(m.value.get("weather_risk_score", 0)),
                default=None,
            )
            if worst is None:
                out.append(
                    WeatherRiskEvaluation(
                        supplier=b.agent_id,
                        origin=origin,
                        risk_level="unknown",
                        source_claim_ids=[m.claim_id for m in matches],
                    )
                )
                continue

            score = float(worst.value.get("weather_risk_score"))
            level = _level_for_score(score)
            forecast = worst.value.get("forecast")
            reason = (
                f"weather_risk_score={score:.2f} for {origin}"
                + (f" — {forecast}" if forecast else "")
            )
            out.append(
                WeatherRiskEvaluation(
                    supplier=b.agent_id,
                    origin=origin,
                    risk_level=level,
                    score=score,
                    reason=reason,
                    source_claim_ids=[worst.claim_id],
                )
            )

        out.sort(key=lambda e: e.supplier)
        return out

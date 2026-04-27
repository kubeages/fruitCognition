"""Policy guardrail: per-option allowed/requires_human_approval verdict.

Runs AFTER the cost + weather engines (per SPEC §4.8). Reads their
outputs plus the raw claims/beliefs to decide which supply options the
DecisionEngine (iter 14) is allowed to pick from autonomously.

Verdict semantics:
  * allowed=True                              -> DecisionEngine may pick.
  * allowed=False, requires_human_approval=T  -> needs human approval to proceed.
  * allowed=False, requires_human_approval=F  -> hard-blocked.

A violation is "approval-redeemable" if it appears in
``intent.human_approval_required_if``; otherwise it is a hard block.
"""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel

from cognition.engines.cost_engine import CostEvaluation
from cognition.engines.weather_risk_engine import WeatherRiskEvaluation
from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


_QUALITY_LOW_THRESHOLD = 0.6


class GuardrailVerdict(BaseModel):
    supplier: str
    allowed: bool
    requires_human_approval: bool
    violations: list[str] = []
    rationale: str | None = None


class PolicyGuardrailEngine:
    def evaluate(
        self,
        *,
        intent: IntentContract,
        claims: Iterable[Claim],
        beliefs: Iterable[Belief],
        cost: Iterable[CostEvaluation],
        weather: Iterable[WeatherRiskEvaluation],
    ) -> list[GuardrailVerdict]:
        beliefs = list(beliefs)
        claims = list(claims)
        cost_by_supplier = {c.supplier: c for c in cost}
        weather_by_supplier = {w.supplier: w for w in weather}

        # delivery_sla claims keyed by agent_id (best-effort: each shipping/farm agent
        # may report its own ETA).
        sla_eta_by_agent: dict[str, int] = {}
        for c in claims:
            if c.claim_type != "delivery_sla":
                continue
            eta = c.value.get("eta_days") or c.value.get("sla_days")
            if eta is not None:
                sla_eta_by_agent[c.agent_id] = int(eta)

        approval_redeemable = set(intent.human_approval_required_if or [])
        quality_threshold = float(
            intent.hard_constraints.get("min_quality_score", _QUALITY_LOW_THRESHOLD)
            if isinstance(intent.hard_constraints, dict) else _QUALITY_LOW_THRESHOLD
        )

        verdicts: list[GuardrailVerdict] = []
        for b in beliefs:
            if b.belief_type != "supply_option":
                continue
            violations: list[str] = []

            ce = cost_by_supplier.get(b.agent_id)
            if ce and ce.within_budget is False:
                violations.append("price_above_budget")

            we = weather_by_supplier.get(b.agent_id)
            if we and we.risk_level == "high":
                violations.append("weather_risk_high")

            eta = sla_eta_by_agent.get(b.agent_id)
            if eta is not None and intent.delivery_days is not None and eta > intent.delivery_days:
                violations.append("delivery_sla_at_risk")

            q = b.value.get("quality_score")
            if q is not None and float(q) < quality_threshold:
                violations.append("quality_below_threshold")

            if not violations:
                verdicts.append(
                    GuardrailVerdict(
                        supplier=b.agent_id,
                        allowed=True,
                        requires_human_approval=False,
                        rationale="No policy violations detected.",
                    )
                )
                continue

            redeemable = [v for v in violations if v in approval_redeemable]
            non_redeemable = [v for v in violations if v not in approval_redeemable]

            if non_redeemable:
                # Anything outside the approval allow-list is a hard block.
                verdicts.append(
                    GuardrailVerdict(
                        supplier=b.agent_id,
                        allowed=False,
                        requires_human_approval=False,
                        violations=violations,
                        rationale="Hard-blocked: " + ", ".join(non_redeemable),
                    )
                )
            else:
                verdicts.append(
                    GuardrailVerdict(
                        supplier=b.agent_id,
                        allowed=False,
                        requires_human_approval=True,
                        violations=violations,
                        rationale="Requires human approval: " + ", ".join(redeemable),
                    )
                )

        verdicts.sort(key=lambda v: v.supplier)
        return verdicts

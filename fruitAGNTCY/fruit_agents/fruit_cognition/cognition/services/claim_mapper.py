from __future__ import annotations

from typing import Any

from cognition.schemas.claim import Claim
from cognition.schemas.evidence import evidence_ref


class ClaimMapper:
    """Translate raw agent responses into typed Claim objects.

    Each ``map_*`` method takes a flat response dict and fans it out
    into one or more claims. Missing fields are skipped silently — the
    mapper is intentionally permissive so partial agent responses
    still produce whatever claims they support.
    """

    # ----- farm-shaped responses -----

    def map_farm_response(
        self,
        *,
        intent_id: str,
        agent_id: str,
        response: dict[str, Any],
    ) -> list[Claim]:
        claims: list[Claim] = []
        subject = response.get("fruit_type") or response.get("subject") or "unknown"
        confidence = float(response.get("confidence", 1.0))
        ref = evidence_ref("farm", agent_id)

        if "available_lb" in response:
            claims.append(
                Claim(
                    intent_id=intent_id,
                    agent_id=agent_id,
                    claim_type="inventory",
                    subject=subject,
                    value={
                        "available_lb": response["available_lb"],
                        "origin": response.get("origin"),
                        "fruit_type": subject,
                    },
                    confidence=confidence,
                    evidence_refs=[ref],
                )
            )
        if "unit_price_usd" in response:
            claims.append(
                Claim(
                    intent_id=intent_id,
                    agent_id=agent_id,
                    claim_type="price",
                    subject=subject,
                    value={
                        "unit_price_usd": response["unit_price_usd"],
                        "currency": response.get("currency", "USD"),
                    },
                    confidence=confidence,
                    evidence_refs=[ref],
                )
            )
        if "quality_score" in response:
            claims.append(
                Claim(
                    intent_id=intent_id,
                    agent_id=agent_id,
                    claim_type="quality",
                    subject=subject,
                    value={"quality_score": response["quality_score"]},
                    confidence=confidence,
                    evidence_refs=[ref],
                )
            )
        if "origin" in response:
            claims.append(
                Claim(
                    intent_id=intent_id,
                    agent_id=agent_id,
                    claim_type="origin",
                    subject=subject,
                    value={"origin": response["origin"]},
                    confidence=confidence,
                    evidence_refs=[ref],
                )
            )
        return claims

    # ----- weather-shaped responses -----

    def map_weather_response(
        self,
        *,
        intent_id: str,
        agent_id: str,
        response: dict[str, Any],
    ) -> list[Claim]:
        if "weather_risk_score" not in response and "forecast" not in response:
            return []
        return [
            Claim(
                intent_id=intent_id,
                agent_id=agent_id,
                claim_type="weather_risk",
                subject=response.get("region", "unknown"),
                value={
                    k: response[k]
                    for k in ("weather_risk_score", "forecast", "region", "horizon_days")
                    if k in response
                },
                confidence=float(response.get("confidence", 1.0)),
                evidence_refs=[evidence_ref("weather", agent_id)],
            )
        ]

    # ----- logistics-shaped responses -----

    def map_logistics_response(
        self,
        *,
        intent_id: str,
        agent_id: str,
        response: dict[str, Any],
    ) -> list[Claim]:
        claims: list[Claim] = []
        subject = response.get("route") or response.get("subject") or "shipment"
        confidence = float(response.get("confidence", 1.0))
        ref = evidence_ref("logistics", agent_id)

        if "capacity_lb" in response:
            claims.append(
                Claim(
                    intent_id=intent_id,
                    agent_id=agent_id,
                    claim_type="shipping_capacity",
                    subject=subject,
                    value={"capacity_lb": response["capacity_lb"]},
                    confidence=confidence,
                    evidence_refs=[ref],
                )
            )
        if "shipping_cost_usd" in response:
            claims.append(
                Claim(
                    intent_id=intent_id,
                    agent_id=agent_id,
                    claim_type="shipping_cost",
                    subject=subject,
                    value={"shipping_cost_usd": response["shipping_cost_usd"]},
                    confidence=confidence,
                    evidence_refs=[ref],
                )
            )
        if "eta_days" in response or "sla_days" in response:
            claims.append(
                Claim(
                    intent_id=intent_id,
                    agent_id=agent_id,
                    claim_type="delivery_sla",
                    subject=subject,
                    value={
                        k: response[k]
                        for k in ("eta_days", "sla_days", "carrier")
                        if k in response
                    },
                    confidence=confidence,
                    evidence_refs=[ref],
                )
            )
        return claims

    # ----- payment-shaped responses -----

    def map_payment_response(
        self,
        *,
        intent_id: str,
        agent_id: str,
        response: dict[str, Any],
    ) -> list[Claim]:
        if "status" not in response:
            return []
        return [
            Claim(
                intent_id=intent_id,
                agent_id=agent_id,
                claim_type="payment_status",
                subject=response.get("order_id", "unknown"),
                value={
                    k: response[k]
                    for k in ("status", "amount_usd", "currency", "order_id")
                    if k in response
                },
                confidence=float(response.get("confidence", 1.0)),
                evidence_refs=[evidence_ref("payment", agent_id)],
            )
        ]

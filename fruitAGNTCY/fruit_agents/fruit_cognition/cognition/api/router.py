"""Read-only HTTP surface for the cognition fabric.

Mounted on any FastAPI app that wants to expose cognition state. The
router only reads — writes happen inside supervisor graphs (intents +
claims) and via the admin Postgres swap endpoint.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract
from cognition.services.belief_builder import BeliefBuilder
from cognition.services.cognition_fabric import get_fabric


_belief_builder = BeliefBuilder()


class IntentSummary(BaseModel):
    intent_id: str
    goal: str
    fruit_type: str | None = None
    quantity_lb: float | None = None
    status: str


class IntentListResponse(BaseModel):
    items: list[IntentSummary]


class IntentStateResponse(BaseModel):
    intent: IntentContract
    claims: list[Claim] = Field(default_factory=list)
    beliefs: list[Belief] = Field(default_factory=list)


def _summary(intent: IntentContract) -> IntentSummary:
    return IntentSummary(
        intent_id=intent.intent_id,
        goal=intent.goal,
        fruit_type=intent.fruit_type,
        quantity_lb=intent.quantity_lb,
        status=intent.status.value,
    )


def create_cognition_router() -> APIRouter:
    router = APIRouter(prefix="/cognition", tags=["cognition"])

    @router.get("/intents", response_model=IntentListResponse)
    async def list_intents() -> IntentListResponse:
        fabric = get_fabric()
        return IntentListResponse(items=[_summary(i) for i in fabric.list_intents()])

    @router.get("/intent/{intent_id}", response_model=IntentContract)
    async def get_intent(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> IntentContract:
        intent = get_fabric().get_intent(intent_id)
        if intent is None:
            raise HTTPException(status_code=404, detail=f"intent {intent_id!r} not found")
        return intent

    @router.get("/intent/{intent_id}/claims", response_model=list[Claim])
    async def list_claims(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> list[Claim]:
        # Don't 404 on no claims — empty list is the right semantic.
        return get_fabric().list_claims(intent_id)

    @router.get("/intent/{intent_id}/beliefs", response_model=list[Belief])
    async def list_beliefs(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> list[Belief]:
        # Built on the fly from the current claims — beliefs are not persisted yet.
        claims = get_fabric().list_claims(intent_id)
        return _belief_builder.build(intent_id=intent_id, claims=claims)

    @router.get("/intent/{intent_id}/state", response_model=IntentStateResponse)
    async def get_state(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> IntentStateResponse:
        fabric = get_fabric()
        intent = fabric.get_intent(intent_id)
        if intent is None:
            raise HTTPException(status_code=404, detail=f"intent {intent_id!r} not found")
        claims = fabric.list_claims(intent_id)
        beliefs = _belief_builder.build(intent_id=intent_id, claims=claims)
        return IntentStateResponse(intent=intent, claims=claims, beliefs=beliefs)

    return router

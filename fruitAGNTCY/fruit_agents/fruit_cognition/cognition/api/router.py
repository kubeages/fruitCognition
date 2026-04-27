"""Read-only HTTP surface for the cognition fabric.

Mounted on any FastAPI app that wants to expose cognition state. The
router only reads — writes happen inside supervisor graphs (intents +
claims) and via the admin Postgres swap endpoint.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from cognition.schemas.approval import ApprovalRequest, ApprovalResult
from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.conflict import Conflict
from cognition.schemas.decision import Decision
from cognition.schemas.intent_contract import IntentContract
from cognition.schemas.plan import Plan
from cognition.services import approval_service
from cognition.services.approval_service import (
    ApprovalNotFound,
    ApprovalNotPending,
)
from cognition.services.belief_builder import BeliefBuilder
from cognition.services.cognition_fabric import get_fabric
from cognition.services.engine_pipeline import (
    EvaluatedOption,
    evaluate_intent,
)


_belief_builder = BeliefBuilder()


class ApprovalActionPayload(BaseModel):
    note: str | None = None


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
    conflicts: list[Conflict] = Field(default_factory=list)
    options: list[EvaluatedOption] = Field(default_factory=list)
    plans: list[Plan] = Field(default_factory=list)
    decision: Decision | None = None


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

    @router.get("/intent/{intent_id}/conflicts", response_model=list[Conflict])
    async def list_conflicts(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> list[Conflict]:
        evaluation = evaluate_intent(intent_id)
        if evaluation is None:
            raise HTTPException(status_code=404, detail=f"intent {intent_id!r} not found")
        return evaluation.conflicts

    @router.get("/intent/{intent_id}/options", response_model=list[EvaluatedOption])
    async def list_options(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> list[EvaluatedOption]:
        evaluation = evaluate_intent(intent_id)
        if evaluation is None:
            raise HTTPException(status_code=404, detail=f"intent {intent_id!r} not found")
        return evaluation.options

    @router.get("/intent/{intent_id}/plans", response_model=list[Plan])
    async def list_plans(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> list[Plan]:
        evaluation = evaluate_intent(intent_id)
        if evaluation is None:
            raise HTTPException(status_code=404, detail=f"intent {intent_id!r} not found")
        return evaluation.plans

    @router.get("/intent/{intent_id}/decision", response_model=Decision)
    async def get_decision(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> Decision:
        evaluation = evaluate_intent(intent_id)
        if evaluation is None:
            raise HTTPException(status_code=404, detail=f"intent {intent_id!r} not found")
        if evaluation.decision is None:  # pragma: no cover — pipeline always returns one
            raise HTTPException(status_code=500, detail="decision not available")
        return evaluation.decision

    # ----- approval flow (iter 15) -----

    @router.get("/approvals", response_model=list[ApprovalRequest])
    async def list_approvals() -> list[ApprovalRequest]:
        return approval_service.list_pending()

    @router.get("/approval/{intent_id}", response_model=ApprovalRequest)
    async def get_approval(
        intent_id: Annotated[str, Path(min_length=1)],
    ) -> ApprovalRequest:
        try:
            return approval_service.get_approval(intent_id)
        except ApprovalNotFound:
            raise HTTPException(status_code=404, detail=f"intent {intent_id!r} not found")
        except ApprovalNotPending:
            raise HTTPException(status_code=409, detail="no decision pending for this intent")

    def _to_response(call) -> ApprovalResult:
        try:
            return call()
        except ApprovalNotFound as e:
            raise HTTPException(status_code=404, detail=f"intent {str(e)!r} not found")
        except ApprovalNotPending:
            raise HTTPException(status_code=409, detail="intent is in a terminal state")

    @router.post("/intent/{intent_id}/approve", response_model=ApprovalResult)
    async def approve_intent(
        intent_id: Annotated[str, Path(min_length=1)],
        payload: ApprovalActionPayload = ApprovalActionPayload(),
    ) -> ApprovalResult:
        return _to_response(lambda: approval_service.approve(intent_id, payload.note))

    @router.post("/intent/{intent_id}/reject", response_model=ApprovalResult)
    async def reject_intent(
        intent_id: Annotated[str, Path(min_length=1)],
        payload: ApprovalActionPayload = ApprovalActionPayload(),
    ) -> ApprovalResult:
        return _to_response(lambda: approval_service.reject(intent_id, payload.note))

    @router.post(
        "/intent/{intent_id}/request-alternative", response_model=ApprovalResult,
    )
    async def request_alternative_intent(
        intent_id: Annotated[str, Path(min_length=1)],
        payload: ApprovalActionPayload = ApprovalActionPayload(),
    ) -> ApprovalResult:
        return _to_response(
            lambda: approval_service.request_alternative(intent_id, payload.note)
        )

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
        evaluation = evaluate_intent(intent_id)
        return IntentStateResponse(
            intent=intent,
            claims=claims,
            beliefs=beliefs,
            conflicts=evaluation.conflicts if evaluation else [],
            options=evaluation.options if evaluation else [],
            plans=evaluation.plans if evaluation else [],
            decision=evaluation.decision if evaluation else None,
        )

    return router

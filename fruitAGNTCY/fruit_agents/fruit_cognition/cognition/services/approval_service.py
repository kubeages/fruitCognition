"""Approval service: list pending approvals, accept approve/reject/
request-alternative actions and update intent status.

Demo-grade: no auth (per SPEC iter 15 §Acceptance). Persistence is
just intent.status, written back to the active fabric — Decision is
recomputed from claims on demand.
"""

from __future__ import annotations

import logging

from cognition.schemas.approval import ApprovalAction, ApprovalRequest, ApprovalResult
from cognition.schemas.intent_contract import IntentStatus
from cognition.services.cognition_fabric import get_fabric
from cognition.services.engine_pipeline import evaluate_intent


logger = logging.getLogger("fruit_cognition.cognition.approval")


class ApprovalNotFound(Exception):
    pass


class ApprovalNotPending(Exception):
    pass


def _is_terminal(status: IntentStatus) -> bool:
    return status in (
        IntentStatus.APPROVED,
        IntentStatus.REJECTED,
        IntentStatus.COMMITTED,
        IntentStatus.FAILED,
    )


def list_pending() -> list[ApprovalRequest]:
    """Return one ApprovalRequest per intent whose current decision needs approval."""
    fabric = get_fabric()
    out: list[ApprovalRequest] = []
    for intent in fabric.list_intents():
        if _is_terminal(intent.status):
            continue
        evaluation = evaluate_intent(intent.intent_id)
        if evaluation is None or evaluation.decision is None:
            continue
        if evaluation.decision.requires_human_approval:
            # Promote status to APPROVAL_REQUIRED on first observation.
            if intent.status != IntentStatus.APPROVAL_REQUIRED:
                intent = intent.model_copy(update={"status": IntentStatus.APPROVAL_REQUIRED})
                fabric.save_intent(intent)
            out.append(ApprovalRequest(intent=intent, decision=evaluation.decision))
    return out


def get_approval(intent_id: str) -> ApprovalRequest:
    fabric = get_fabric()
    intent = fabric.get_intent(intent_id)
    if intent is None:
        raise ApprovalNotFound(intent_id)
    evaluation = evaluate_intent(intent_id)
    if evaluation is None or evaluation.decision is None:
        raise ApprovalNotPending(intent_id)
    return ApprovalRequest(intent=intent, decision=evaluation.decision)


def _apply_action(intent_id: str, action: ApprovalAction, note: str | None) -> ApprovalResult:
    fabric = get_fabric()
    intent = fabric.get_intent(intent_id)
    if intent is None:
        raise ApprovalNotFound(intent_id)
    if _is_terminal(intent.status):
        raise ApprovalNotPending(intent_id)

    new_status: IntentStatus
    if action == "approve":
        new_status = IntentStatus.APPROVED
    elif action == "reject":
        new_status = IntentStatus.REJECTED
    elif action == "request_alternative":
        # Bounce back to GROUNDING so a re-run can produce a different decision.
        new_status = IntentStatus.GROUNDING
    else:  # pragma: no cover — Literal type prevents this
        raise ValueError(f"unknown action: {action}")

    fabric.save_intent(intent.model_copy(update={"status": new_status}))
    logger.info(
        "approval action=%s intent=%s status=%s -> %s",
        action, intent_id, intent.status.value, new_status.value,
    )
    return ApprovalResult(
        intent_id=intent_id, action=action, new_status=new_status.value, note=note,
    )


def approve(intent_id: str, note: str | None = None) -> ApprovalResult:
    return _apply_action(intent_id, "approve", note)


def reject(intent_id: str, note: str | None = None) -> ApprovalResult:
    return _apply_action(intent_id, "reject", note)


def request_alternative(intent_id: str, note: str | None = None) -> ApprovalResult:
    return _apply_action(intent_id, "request_alternative", note)

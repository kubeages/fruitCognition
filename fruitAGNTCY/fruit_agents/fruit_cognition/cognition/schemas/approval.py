from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from cognition.schemas.decision import Decision
from cognition.schemas.intent_contract import IntentContract


ApprovalAction = Literal["approve", "reject", "request_alternative"]


class ApprovalRequest(BaseModel):
    """An item in the decisions inbox: an intent + the decision pending approval."""

    intent: IntentContract
    decision: Decision


class ApprovalResult(BaseModel):
    intent_id: str
    action: ApprovalAction
    new_status: str
    note: str | None = None

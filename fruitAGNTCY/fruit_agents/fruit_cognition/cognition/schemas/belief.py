from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Belief(BaseModel):
    """A roll-up over one or more claims about the same subject.

    Example: a ``supply_option`` belief about ``mango`` from
    ``colombia-mango-farm`` collects the inventory + price + quality +
    origin claims and exposes them as a single decidable option.
    """

    belief_id: str = Field(default_factory=lambda: f"belief-{uuid4()}")
    intent_id: str
    belief_type: str
    subject: str
    # The agent or aggregate the belief is about (often equals one of the
    # source claims' agent_id; "aggregate" when synthesized across many).
    agent_id: str
    value: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    source_claim_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

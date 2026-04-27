from __future__ import annotations

from datetime import datetime, timezone


def evidence_ref(source_type: str, agent_id: str, identifier: str | None = None) -> str:
    """Build a Claim.evidence_refs entry of the form ``<source>:<agent>:<id>``.

    `identifier` defaults to the current UTC timestamp when omitted, so a
    ref like ``inventory:colombia-mango-farm:2026-04-27T18:30:00+00:00``
    is unique per emission.
    """
    if identifier is None:
        identifier = datetime.now(timezone.utc).isoformat()
    return f"{source_type}:{agent_id}:{identifier}"

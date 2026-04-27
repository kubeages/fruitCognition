"""Extract structured fields from freeform agent response text.

Farm/logistics agents return prose like
    "Colombia mango farm has 320 lbs available at $2.10/lb. Quality 92%."
The supervisor graph then runs that string through an LLM for the chat
reply. The cognition layer also wants typed claims out of it, so this
module does a heuristic regex pass to recover the most common fields.

The output is a flat dict suitable for ClaimMapper.map_farm_response
or .map_logistics_response. Missing fields are simply omitted; the
mapper is permissive.

When the extractor finds nothing useful, callers get an empty dict and
should skip emitting claims for that response.
"""

from __future__ import annotations

import os
import re
from typing import Any


_QUANTITY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds)\b", re.IGNORECASE)
_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_QUALITY_PCT_RE = re.compile(r"(?:quality|grade)[^0-9%]{0,20}(\d{1,3})\s*%", re.IGNORECASE)
_QUALITY_DEC_RE = re.compile(r"(?:quality|score)[^0-9]{0,20}(0?\.\d+)", re.IGNORECASE)
_ETA_DAYS_RE = re.compile(r"(?:eta|deliver(?:y|ed)?\s+in|within)\s+(\d+)\s+days?", re.IGNORECASE)
_COST_RE = re.compile(r"(?:shipping|cost|freight)[^$]{0,30}\$\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


_FRUITS = ("mango", "apple", "banana", "strawberry")
_ORIGINS = ("colombia", "brazil", "vietnam", "argentina", "ecuador", "kenya")


def extraction_enabled() -> bool:
    """Read COGNITION_CLAIM_EXTRACTION env var (default on)."""
    raw = os.getenv("COGNITION_CLAIM_EXTRACTION", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def extract_farm_text(text: str, *, default_origin: str | None = None) -> dict[str, Any]:
    """Pull inventory/price/quality/origin/fruit_type out of a farm reply.

    Returns ``{}`` if no useful field is found.
    """
    out: dict[str, Any] = {}
    lowered = text.lower()

    for fruit in _FRUITS:
        if fruit in lowered:
            out["fruit_type"] = fruit
            break

    qm = _QUANTITY_RE.search(text)
    if qm:
        out["available_lb"] = float(qm.group(1))

    pm = _PRICE_RE.search(text)
    if pm:
        out["unit_price_usd"] = float(pm.group(1))

    qpm = _QUALITY_PCT_RE.search(text)
    if qpm:
        out["quality_score"] = round(int(qpm.group(1)) / 100.0, 3)
    else:
        qdm = _QUALITY_DEC_RE.search(text)
        if qdm:
            out["quality_score"] = float(qdm.group(1))

    if default_origin:
        out["origin"] = default_origin
    else:
        for origin in _ORIGINS:
            if origin in lowered:
                out["origin"] = origin
                break

    return out


def extract_logistics_text(text: str) -> dict[str, Any]:
    """Pull shipping_cost / eta_days out of a logistics reply."""
    out: dict[str, Any] = {}

    cm = _COST_RE.search(text)
    if cm:
        out["shipping_cost_usd"] = float(cm.group(1))

    em = _ETA_DAYS_RE.search(text)
    if em:
        out["eta_days"] = int(em.group(1))

    return out

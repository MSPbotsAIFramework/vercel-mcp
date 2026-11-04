"""Token-economy helpers for tool return values (SOP §2.5).

Tool results go straight into the agent's context window, so list results
are capped, trimmed to the fields an agent needs, and serialized compactly.
"""

from __future__ import annotations

import json
from typing import Any

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_RESPONSE_CHARS = 20_000


def clamp_limit(limit: int | None) -> int:
    """Clamp a caller-supplied `limit` to (0, MAX_LIMIT], defaulting to DEFAULT_LIMIT."""
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def dumps(payload: Any) -> str:
    """Serialize compactly; if a `{"items": [...]}` payload is too large, trim
    the list and flag `has_more` rather than ever returning an unbounded blob.
    """
    text = _compact(payload)
    if len(text) <= MAX_RESPONSE_CHARS:
        return text

    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = list(payload["items"])
        while items:
            items.pop()
            candidate = {**payload, "items": items, "has_more": True}
            candidate_text = _compact(candidate)
            if len(candidate_text) <= MAX_RESPONSE_CHARS:
                return candidate_text
        return _compact({**payload, "items": [], "has_more": True})

    # No list to trim: this should not happen for the tools in this service
    # (every large-payload tool returns a capped "items" list), but truncate
    # defensively rather than ever exceeding the budget.
    return text[:MAX_RESPONSE_CHARS]


def _compact(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

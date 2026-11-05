"""Structured error envelope for tool failures.

Tools never raise exceptions past their boundary — every failure is returned
as a JSON string the agent can branch on. See docs/tickets/PRD-21334.md
"Tech design > Data & API contract" for the fixed error-code vocabulary.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar


@dataclass(frozen=True)
class ToolError(Exception):
    """A structured, user-facing tool error."""

    code: str
    message: str
    retryable: bool = False

    def to_json(self) -> str:
        return json.dumps(
            {"error": {"code": self.code, "message": self.message, "retryable": self.retryable}},
            separators=(",", ":"),
            ensure_ascii=False,
        )


def not_configured(message: str) -> ToolError:
    return ToolError(code="not_configured", message=message, retryable=False)


def unauthorized(message: str) -> ToolError:
    return ToolError(code="unauthorized", message=message, retryable=False)


def not_found(message: str) -> ToolError:
    return ToolError(code="not_found", message=message, retryable=False)


def invalid_argument(message: str) -> ToolError:
    return ToolError(code="invalid_argument", message=message, retryable=False)


def rate_limited(message: str) -> ToolError:
    return ToolError(code="rate_limited", message=message, retryable=True)


def upstream_error(message: str) -> ToolError:
    return ToolError(code="upstream_error", message=message, retryable=True)


def from_status_code(status_code: int, message: str) -> ToolError:
    """Map a Vercel HTTP status code to the fixed error-code vocabulary."""
    if status_code in (400, 422):
        return invalid_argument(message)
    if status_code in (401, 403):
        return unauthorized(message)
    if status_code == 404:
        return not_found(message)
    if status_code == 429:
        return rate_limited(message)
    if status_code >= 500:
        return upstream_error(message)
    return upstream_error(message)


_F = TypeVar("_F", bound=Callable[..., Awaitable[str]])


def handle_tool_errors(func: _F) -> _F:
    """Wrap a tool coroutine so it never raises past the MCP boundary.

    `ToolError` is serialized to the structured envelope; any other
    exception is treated as an unexpected upstream failure. The message is
    deliberately generic (never the raw exception text) so a credential or
    response body can never leak into a tool result.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ToolError as exc:
            return exc.to_json()
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            return upstream_error(
                f"unexpected error calling the Vercel API ({type(exc).__name__})"
            ).to_json()

    return wrapper  # type: ignore[return-value]

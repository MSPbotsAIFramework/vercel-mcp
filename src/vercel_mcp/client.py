"""HTTP client for the Vercel REST API.

One client is built per tool invocation (request-scoped), carrying only the
credentials set on the current request's contextvar — never a module-level
client or token (SOP §3.3/§3.4).
"""

from __future__ import annotations

import asyncio
import contextvars
from dataclasses import dataclass

import httpx

from vercel_mcp.errors import ToolError, from_status_code, unauthorized
from vercel_mcp.settings import settings

MAX_RETRIES = 2  # 3 attempts total, kept low to respect the <120s call budget
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Test-only hook: lets tests/test_tools.py and tests/test_client.py mock the
# Vercel API with httpx.MockTransport without any code path in production
# ever doing anything but real network I/O (this stays None outside tests).
_default_transport: httpx.BaseTransport | None = None


@dataclass(frozen=True)
class Credentials:
    access_token: str
    team_id: str | None = None


_credentials_var: contextvars.ContextVar["Credentials | None"] = contextvars.ContextVar(
    "vercel_credentials", default=None
)


def set_credentials(creds: "Credentials | None") -> contextvars.Token:
    return _credentials_var.set(creds)


def reset_credentials(token: contextvars.Token) -> None:
    _credentials_var.reset(token)


def get_credentials() -> Credentials:
    creds = _credentials_var.get()
    if creds is None:
        # Defensive only: the HTTP middleware already rejects any request
        # missing the required header before a tool ever runs.
        raise unauthorized("missing Vercel credentials in request context")
    return creds


class VercelClient:
    """Thin async wrapper over httpx for a single tool invocation."""

    def __init__(
        self, credentials: Credentials | None = None, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._credentials = credentials or get_credentials()
        self._transport = transport if transport is not None else _default_transport

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict | list:
        call_params = dict(params or {})
        if self._credentials.team_id:
            call_params["teamId"] = self._credentials.team_id

        headers = {"Authorization": f"Bearer {self._credentials.access_token}"}
        timeout = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0)

        async with httpx.AsyncClient(
            base_url=settings.vercel_api_base_url,
            timeout=timeout,
            headers=headers,
            transport=self._transport,
        ) as client:
            attempt = 0
            while True:
                attempt += 1
                try:
                    response = await client.request(
                        method, path, params=call_params or None, json=json_body
                    )
                except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                    if attempt > MAX_RETRIES:
                        raise ToolError(
                            code="upstream_error",
                            message="Vercel API request failed: network error",
                            retryable=True,
                        ) from exc
                    await asyncio.sleep(_backoff_seconds(attempt))
                    continue

                if response.status_code < 400:
                    if response.status_code == 204 or not response.content:
                        return {}
                    return response.json()

                if response.status_code in RETRYABLE_STATUS and attempt <= MAX_RETRIES:
                    delay = _retry_after_seconds(response)
                    if delay is None:
                        delay = _backoff_seconds(attempt)
                    await asyncio.sleep(delay)
                    continue

                raise from_status_code(response.status_code, _error_message(response))


def _backoff_seconds(attempt: int) -> float:
    return min(2.0 ** (attempt - 1) * 0.5, 8.0)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"Vercel API returned HTTP {response.status_code}"
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
    return f"Vercel API returned HTTP {response.status_code}"

"""Per-request credential extraction and isolation.

Reads tenant credentials from HTTP headers on every MCP request and stores
them in a contextvar scoped to that single request only (SOP §3.3) — never
a global or module-level variable. Requests to the MCP endpoint missing the
required header are rejected with 401 before any tool runs (SOP §3.2, AC10).
`GET /health` is untouched by this middleware (AC13).
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Receive, Scope, Send

from vercel_mcp.client import Credentials, reset_credentials, set_credentials

ACCESS_TOKEN_HEADER = b"x-vercel-access-token"
TEAM_ID_HEADER = b"x-vercel-team-id"


class CredentialsMiddleware:
    """ASGI middleware: extract Vercel credentials for MCP requests only.

    A raw ASGI middleware (not Starlette's `BaseHTTPMiddleware`) is used
    deliberately: Streamable HTTP responses can be long-lived SSE streams,
    and `BaseHTTPMiddleware` buffers the whole response body, which breaks
    streaming.
    """

    def __init__(self, app: ASGIApp, mcp_path: str) -> None:
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != self.mcp_path:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        access_token = headers.get(ACCESS_TOKEN_HEADER)

        if not access_token:
            await _send_missing_header_response(send)
            return

        team_id = headers.get(TEAM_ID_HEADER)
        credentials = Credentials(
            access_token=access_token.decode("latin-1"),
            team_id=team_id.decode("latin-1") if team_id else None,
        )
        token = set_credentials(credentials)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_credentials(token)


async def _send_missing_header_response(send: Send) -> None:
    body = json.dumps(
        {"error": "missing required header(s)", "required": ["X-Vercel-Access-Token"]},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})

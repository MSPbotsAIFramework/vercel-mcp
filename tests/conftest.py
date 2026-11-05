from __future__ import annotations

import contextlib
import json

import httpx
import pytest
from starlette.testclient import TestClient

import vercel_mcp.client as client_module
from vercel_mcp.server import create_app

HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@contextlib.asynccontextmanager
async def running_asgi_client(app):
    """A real-concurrency async client: runs the app's lifespan, then drives
    it over an in-memory ASGI transport (used where TestClient's
    one-request-at-a-time model can't exercise concurrent requests).

    Deliberately a plain async context manager (not a pytest-asyncio
    fixture): the anyio task group backing the MCP session manager's
    lifespan must be entered and exited from the same task, which a
    separately-scoped async fixture cannot guarantee.
    """
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(app.router.lifespan_context(app))
        transport = httpx.ASGITransport(app=app)
        http_client = await stack.enter_async_context(
            httpx.AsyncClient(transport=transport, base_url="http://test")
        )
        yield http_client


@pytest.fixture()
def mock_vercel(monkeypatch):
    """Install an httpx.MockTransport as the Vercel API backend for the
    duration of a test. `handler` receives an `httpx.Request` and returns an
    `httpx.Response` — see httpx.MockTransport docs. Works for both sync and
    async handler functions.
    """

    def _install(handler):
        monkeypatch.setattr(client_module, "_default_transport", httpx.MockTransport(handler))

    return _install


def call_tool(client: TestClient, name: str, arguments: dict, *, access_token: str = "tkn_test", team_id: str | None = None):
    """POST a tools/call request and return the parsed tool result payload."""
    headers = dict(HEADERS)
    if access_token is not None:
        headers["X-Vercel-Access-Token"] = access_token
    if team_id is not None:
        headers["X-Vercel-Team-Id"] = team_id

    response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    return response, _parse_sse_json(response.text)


def list_tools(client: TestClient, *, access_token: str = "tkn_test"):
    headers = dict(HEADERS)
    if access_token is not None:
        headers["X-Vercel-Access-Token"] = access_token
    response = client.post(
        "/mcp",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    return response, _parse_sse_json(response.text)


def _parse_sse_json(text: str) -> dict:
    # The streamable-http transport returns `event: message\ndata: {...}`.
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: ") :])
    return json.loads(text)


def tool_result_text(payload: dict) -> str:
    content = payload["result"]["content"]
    return content[0]["text"]

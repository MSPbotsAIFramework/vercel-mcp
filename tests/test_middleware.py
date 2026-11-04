"""TC1/TC12 (AC10/AC11): missing-header 401, and contextvar isolation."""

from __future__ import annotations

import asyncio

import httpx

from tests.conftest import HEADERS, running_asgi_client


def test_missing_access_token_header_returns_401(client):
    response = client.post(
        "/mcp",
        headers=HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["required"] == ["X-Vercel-Access-Token"]


def test_health_ignores_missing_header(client):
    # /health must never require the credential header (AC13).
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_concurrent_requests_do_not_leak_credentials_across_contextvars(app, mock_vercel):
    seen_authorization: list[str | None] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        # Force interleaving: without per-request isolation, a concurrent
        # second request could overwrite the first request's credentials
        # before this line runs.
        await asyncio.sleep(0.02)
        seen_authorization.append(request.headers.get("authorization"))
        return httpx.Response(200, json={"projects": []})

    mock_vercel(handler)

    async def call(asgi_client: httpx.AsyncClient, token: str) -> httpx.Response:
        return await asgi_client.post(
            "/mcp",
            headers={**HEADERS, "X-Vercel-Access-Token": token},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "vercel_list_projects", "arguments": {}},
            },
        )

    async with running_asgi_client(app) as asgi_client:
        response_a, response_b = await asyncio.gather(
            call(asgi_client, "token-A"), call(asgi_client, "token-B")
        )

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert sorted(seen_authorization) == ["Bearer token-A", "Bearer token-B"]

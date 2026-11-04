"""TC15 (AC10): 429 with Retry-After is retried with backoff, then surfaces rate_limited."""

from __future__ import annotations

import httpx
import pytest

from vercel_mcp.client import Credentials, VercelClient
from vercel_mcp.errors import ToolError


async def test_429_retried_with_backoff_then_rate_limited_error():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        return httpx.Response(429, headers={"Retry-After": "0"}, json={"error": {"message": "rate limited"}})

    client = VercelClient(
        credentials=Credentials(access_token="tkn"),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ToolError) as excinfo:
        await client.request("GET", "/v10/projects")

    assert excinfo.value.code == "rate_limited"
    assert excinfo.value.retryable is True
    # MAX_RETRIES=2 -> 3 attempts total (1 initial + 2 retries) before giving up.
    assert len(attempts) == 3


async def test_success_after_one_retryable_5xx():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        if len(attempts) == 1:
            return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})
        return httpx.Response(200, json={"projects": []})

    client = VercelClient(
        credentials=Credentials(access_token="tkn"),
        transport=httpx.MockTransport(handler),
    )

    result = await client.request("GET", "/v10/projects")
    assert result == {"projects": []}
    assert len(attempts) == 2


async def test_team_id_forwarded_as_query_param():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["teamId"] = request.url.params.get("teamId")
        return httpx.Response(200, json={"projects": []})

    client = VercelClient(
        credentials=Credentials(access_token="tkn", team_id="team_123"),
        transport=httpx.MockTransport(handler),
    )

    await client.request("GET", "/v10/projects")
    assert captured["teamId"] == "team_123"

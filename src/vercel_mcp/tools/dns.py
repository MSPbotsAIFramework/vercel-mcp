"""Tools for DNS records on domains managed through this connector."""

from __future__ import annotations

from fastmcp import FastMCP

from vercel_mcp.client import VercelClient
from vercel_mcp.errors import handle_tool_errors
from vercel_mcp.serialize import clamp_limit, dumps


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_list_dns_records(domain: str, limit: int = 50) -> str:
        """List DNS records for a domain.

        Args:
            domain: The domain name, e.g. "example.com".
            limit: Max records to return (default 50, hard cap 200).
        """
        client = VercelClient()
        data = await client.request(
            "GET", f"/v5/domains/{domain}/records", params={"limit": clamp_limit(limit)}
        )
        records = data.get("records", []) if isinstance(data, dict) else data
        return dumps({"items": [_record_summary(r) for r in records]})

    @mcp.tool
    @handle_tool_errors
    async def vercel_create_dns_record(
        domain: str, type: str, name: str, value: str, ttl: int | None = None
    ) -> str:
        """Create a DNS record on a domain.

        Args:
            domain: The domain name, e.g. "example.com".
            type: Record type, e.g. "A", "CNAME", "TXT", "MX".
            name: Record name/subdomain (use "" or "@" for the apex).
            value: Record value.
            ttl: Time-to-live in seconds; omit to use Vercel's default.
        """
        client = VercelClient()
        body: dict = {"type": type, "name": name, "value": value}
        if ttl is not None:
            body["ttl"] = ttl
        data = await client.request("POST", f"/v2/domains/{domain}/records", json_body=body)
        return dumps(_record_summary(data))

    @mcp.tool(annotations={"destructiveHint": True, "idempotentHint": True})
    @handle_tool_errors
    async def vercel_delete_dns_record(domain: str, record_id: str) -> str:
        """Delete a DNS record from a domain.

        Args:
            domain: The domain name, e.g. "example.com".
            record_id: The DNS record id to delete.
        """
        client = VercelClient()
        await client.request("DELETE", f"/v2/domains/{domain}/records/{record_id}")
        return dumps({"deleted": True, "id": record_id})


def _record_summary(record: dict) -> dict:
    return {
        "id": record.get("id") or record.get("uid"),
        "type": record.get("type"),
        "name": record.get("name"),
        "value": record.get("value"),
        "ttl": record.get("ttl"),
    }

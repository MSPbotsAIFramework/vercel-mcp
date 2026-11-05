"""Tools for a project's custom domains."""

from __future__ import annotations

from fastmcp import FastMCP

from vercel_mcp.client import VercelClient
from vercel_mcp.errors import handle_tool_errors
from vercel_mcp.serialize import clamp_limit, dumps


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_list_domains(limit: int = 50) -> str:
        """List domains in the account/team.

        Args:
            limit: Max domains to return (default 50, hard cap 200).
        """
        client = VercelClient()
        data = await client.request("GET", "/v5/domains", params={"limit": clamp_limit(limit)})
        domains = data.get("domains", []) if isinstance(data, dict) else data
        return dumps({"items": [_domain_summary(d) for d in domains]})

    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_get_domain(domain: str) -> str:
        """Get a single domain's configuration.

        Args:
            domain: The domain name, e.g. "example.com".
        """
        client = VercelClient()
        data = await client.request("GET", f"/v5/domains/{domain}")
        return dumps(_domain_summary(data))

    @mcp.tool
    @handle_tool_errors
    async def vercel_add_project_domain(project_id_or_name: str, domain: str) -> str:
        """Attach a custom domain to a project.

        Args:
            project_id_or_name: The Vercel project id or name.
            domain: The domain name to attach, e.g. "example.com".
        """
        client = VercelClient()
        data = await client.request(
            "POST", f"/v10/projects/{project_id_or_name}/domains", json_body={"name": domain}
        )
        return dumps(_domain_summary(data))

    @mcp.tool(annotations={"destructiveHint": True, "idempotentHint": True})
    @handle_tool_errors
    async def vercel_remove_project_domain(project_id_or_name: str, domain: str) -> str:
        """Detach a custom domain from a project.

        Args:
            project_id_or_name: The Vercel project id or name.
            domain: The domain name to remove, e.g. "example.com".
        """
        client = VercelClient()
        await client.request("DELETE", f"/v9/projects/{project_id_or_name}/domains/{domain}")
        return dumps({"removed": True, "domain": domain})


def _domain_summary(domain: dict) -> dict:
    return {
        "name": domain.get("name"),
        "verified": domain.get("verified"),
        "project_id": domain.get("projectId"),
    }

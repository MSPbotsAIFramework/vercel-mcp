"""Tools for Vercel projects (read-only)."""

from __future__ import annotations

from fastmcp import FastMCP

from vercel_mcp.client import VercelClient
from vercel_mcp.errors import handle_tool_errors
from vercel_mcp.serialize import clamp_limit, dumps


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_list_projects(limit: int = 50, search: str | None = None) -> str:
        """List the tenant's (or team's) Vercel projects.

        Args:
            limit: Max projects to return (default 50, hard cap 200).
            search: Optional substring filter on project name.
        """
        client = VercelClient()
        params: dict = {"limit": clamp_limit(limit)}
        if search:
            params["search"] = search
        data = await client.request("GET", "/v10/projects", params=params)
        projects = data.get("projects", []) if isinstance(data, dict) else data
        return dumps({"items": [_project_summary(p) for p in projects]})

    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_get_project(project_id_or_name: str) -> str:
        """Get a single Vercel project by id or name.

        Args:
            project_id_or_name: The Vercel project id or name.
        """
        client = VercelClient()
        data = await client.request("GET", f"/v9/projects/{project_id_or_name}")
        return dumps(_project_summary(data))


def _project_summary(project: dict) -> dict:
    latest = project.get("latestDeployments")
    latest_id = None
    if isinstance(latest, list) and latest:
        latest_id = latest[0].get("uid") or latest[0].get("id")
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "framework": project.get("framework"),
        "latest_production_deployment_id": latest_id,
    }

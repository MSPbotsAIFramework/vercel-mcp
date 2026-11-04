"""Tools for Vercel deployments: list/get/logs/create/cancel/delete/promote."""

from __future__ import annotations

from fastmcp import FastMCP

from vercel_mcp.client import VercelClient
from vercel_mcp.errors import handle_tool_errors, invalid_argument
from vercel_mcp.serialize import clamp_limit, dumps


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_list_deployments(
        project_id: str | None = None,
        target: str | None = None,
        state: str | None = None,
        limit: int = 50,
    ) -> str:
        """List deployments, newest first.

        Args:
            project_id: Restrict to one project's deployments.
            target: Filter by target environment, e.g. "production", "preview".
            state: Filter by deployment state, e.g. "READY", "BUILDING", "ERROR".
            limit: Max deployments to return (default 50, hard cap 200).
        """
        client = VercelClient()
        params: dict = {"limit": clamp_limit(limit)}
        if project_id:
            params["projectId"] = project_id
        if target:
            params["target"] = target
        if state:
            params["state"] = state
        data = await client.request("GET", "/v7/deployments", params=params)
        deployments = data.get("deployments", []) if isinstance(data, dict) else data
        return dumps({"items": [_deployment_summary(d) for d in deployments]})

    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_get_deployment(deployment_id_or_url: str) -> str:
        """Get a single deployment by id or url.

        Args:
            deployment_id_or_url: The Vercel deployment id or its url.
        """
        client = VercelClient()
        data = await client.request("GET", f"/v13/deployments/{deployment_id_or_url}")
        return dumps(_deployment_summary(data))

    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_get_deployment_logs(deployment_id: str, limit: int = 50) -> str:
        """Get build/runtime events for a deployment.

        Args:
            deployment_id: The Vercel deployment id.
            limit: Max events to return (default 50, hard cap 200).
        """
        client = VercelClient()
        data = await client.request(
            "GET", f"/v3/deployments/{deployment_id}/events", params={"limit": clamp_limit(limit)}
        )
        events = data if isinstance(data, list) else data.get("events", [])
        items = []
        for event in events:
            payload = event.get("payload")
            text = payload.get("text") if isinstance(payload, dict) else None
            items.append({"type": event.get("type"), "created": event.get("created"), "text": text})
        return dumps({"items": items})

    @mcp.tool
    @handle_tool_errors
    async def vercel_create_deployment(
        project: str, git_ref: str, target: str = "production"
    ) -> str:
        """Start a new deployment for a project from a git ref.

        Not idempotent: Vercel has no idempotency-key support, so retrying
        this call after an ambiguous failure can create a duplicate
        deployment.

        Args:
            project: Project id or name to deploy.
            git_ref: Git branch, tag, or commit sha to deploy.
            target: Target environment, "production" or "preview".
        """
        if not git_ref:
            raise invalid_argument("git_ref is required")
        client = VercelClient()
        body = {"name": project, "project": project, "target": target, "gitSource": {"ref": git_ref}}
        data = await client.request("POST", "/v13/deployments", json_body=body)
        return dumps(_deployment_summary(data))

    @mcp.tool(annotations={"destructiveHint": True, "idempotentHint": True})
    @handle_tool_errors
    async def vercel_cancel_deployment(deployment_id: str) -> str:
        """Cancel a queued or building deployment.

        Args:
            deployment_id: The Vercel deployment id to cancel.
        """
        client = VercelClient()
        data = await client.request("PATCH", f"/v12/deployments/{deployment_id}/cancel")
        return dumps(_deployment_summary(data))

    @mcp.tool(annotations={"destructiveHint": True, "idempotentHint": True})
    @handle_tool_errors
    async def vercel_delete_deployment(deployment_id: str) -> str:
        """Permanently delete a deployment.

        Args:
            deployment_id: The Vercel deployment id to delete.
        """
        client = VercelClient()
        await client.request("DELETE", f"/v13/deployments/{deployment_id}")
        return dumps({"deleted": True, "id": deployment_id})

    @mcp.tool(annotations={"idempotentHint": True})
    @handle_tool_errors
    async def vercel_promote_deployment(project_id: str, deployment_id: str) -> str:
        """Point a project's production traffic at a given deployment.

        Covers both promoting a new deployment and rolling back to an
        older one: pointing production at an older deployment id is the
        rollback.

        Args:
            project_id: The Vercel project id.
            deployment_id: The deployment id to make the production deployment.
        """
        client = VercelClient()
        await client.request("POST", f"/v10/projects/{project_id}/promote/{deployment_id}")
        return dumps({"project_id": project_id, "production_deployment_id": deployment_id})


def _deployment_summary(deployment: dict) -> dict:
    return {
        "id": deployment.get("uid") or deployment.get("id"),
        "url": deployment.get("url"),
        "state": deployment.get("readyState") or deployment.get("state"),
        "target": deployment.get("target"),
        "created": deployment.get("createdAt") or deployment.get("created"),
    }

"""Tools for a project's environment variables.

AC8/AC9 — this connector never returns a decrypted environment-variable
value, even though Vercel's API supports `?decrypt=true`. This is a
deliberate security exclusion (see docs/tickets/PRD-21334.md "Decisions made
by DEV01"): `_env_summary` is an allow-list, so a `value`/`decryptedValue`
key from the upstream response can never leak through it, regardless of
what Vercel returns.
"""

from __future__ import annotations

from fastmcp import FastMCP

from vercel_mcp.client import VercelClient
from vercel_mcp.errors import handle_tool_errors
from vercel_mcp.serialize import dumps


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True})
    @handle_tool_errors
    async def vercel_list_env_vars(project_id_or_name: str, target: str | None = None) -> str:
        """List a project's environment variables: metadata only, never values.

        Args:
            project_id_or_name: The Vercel project id or name.
            target: Optional filter by target environment, e.g. "production".
        """
        client = VercelClient()
        params: dict = {}
        if target:
            params["target"] = target
        # Never request decrypt=true (AC8): this call only ever sees metadata.
        data = await client.request("GET", f"/v10/projects/{project_id_or_name}/env", params=params)
        env_vars = data.get("envs", []) if isinstance(data, dict) else data
        return dumps({"items": [_env_summary(e) for e in env_vars]})

    @mcp.tool
    @handle_tool_errors
    async def vercel_create_env_var(
        project_id_or_name: str,
        key: str,
        value: str,
        target: list[str] | None = None,
        type: str = "encrypted",
    ) -> str:
        """Create an environment variable on a project. Never echoes the value back.

        Args:
            project_id_or_name: The Vercel project id or name.
            key: Environment variable name.
            value: Environment variable value (never returned in the response).
            target: Target environments, e.g. ["production", "preview"].
            type: Vercel variable type: "encrypted", "plain", or "sensitive".
        """
        client = VercelClient()
        body = {"key": key, "value": value, "target": target or ["production"], "type": type}
        data = await client.request("POST", f"/v10/projects/{project_id_or_name}/env", json_body=body)
        return dumps(_env_summary(data))

    @mcp.tool(annotations={"destructiveHint": True, "idempotentHint": True})
    @handle_tool_errors
    async def vercel_delete_env_var(project_id_or_name: str, env_id: str) -> str:
        """Delete an environment variable by id.

        Args:
            project_id_or_name: The Vercel project id or name.
            env_id: The environment variable id to delete.
        """
        client = VercelClient()
        await client.request("DELETE", f"/v9/projects/{project_id_or_name}/env/{env_id}")
        return dumps({"deleted": True, "id": env_id})


def _env_summary(env_var: dict) -> dict:
    # Allow-list only: no "value" / "decryptedValue" key is ever constructed
    # here, regardless of what the upstream payload contains.
    return {
        "id": env_var.get("id"),
        "key": env_var.get("key"),
        "target": env_var.get("target"),
        "type": env_var.get("type"),
    }

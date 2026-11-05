"""TC2/TC10/TC14 (AC12/AC8/AC10): tools/list shape, env-var stripping, error mapping."""

from __future__ import annotations

import json

import httpx

from tests.conftest import call_tool, list_tools, tool_result_text

DESTRUCTIVE_TOOLS = {
    "vercel_cancel_deployment",
    "vercel_delete_deployment",
    "vercel_remove_project_domain",
    "vercel_delete_dns_record",
    "vercel_delete_env_var",
}
READ_ONLY_TOOLS = {
    "vercel_list_projects",
    "vercel_get_project",
    "vercel_list_deployments",
    "vercel_get_deployment",
    "vercel_get_deployment_logs",
    "vercel_list_domains",
    "vercel_get_domain",
    "vercel_list_dns_records",
    "vercel_list_env_vars",
}


def test_tool_list_annotations_match_contract(client):
    _, payload = list_tools(client)
    tools = {t["name"]: t.get("annotations", {}) for t in payload["result"]["tools"]}

    assert len(tools) == 19
    assert tools.keys() >= DESTRUCTIVE_TOOLS | READ_ONLY_TOOLS

    for name in DESTRUCTIVE_TOOLS:
        assert tools[name].get("destructiveHint") is True, name

    for name in READ_ONLY_TOOLS:
        assert tools[name].get("readOnlyHint") is True, name
        assert not tools[name].get("destructiveHint"), name


def test_list_env_vars_never_returns_decrypted_value(client, mock_vercel):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "envs": [
                    {
                        "id": "env_1",
                        "key": "DB_PASSWORD",
                        "target": ["production"],
                        "type": "encrypted",
                        "value": "super-secret",
                        "decryptedValue": "super-secret",
                    }
                ]
            },
        )

    mock_vercel(handler)

    _, payload = call_tool(
        client, "vercel_list_env_vars", {"project_id_or_name": "prj_1"}
    )
    text = tool_result_text(payload)
    assert "DB_PASSWORD" in text
    assert "value" not in json.loads(text)["items"][0]
    assert "super-secret" not in text


def test_upstream_404_maps_to_structured_not_found(client, mock_vercel):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"message": "deployment dpl_x not found"}})

    mock_vercel(handler)

    _, payload = call_tool(client, "vercel_get_deployment", {"deployment_id_or_url": "dpl_x"})
    text = tool_result_text(payload)
    body = json.loads(text)
    assert body["error"]["code"] == "not_found"
    assert body["error"]["retryable"] is False


def test_cancel_on_already_finished_deployment_returns_structured_error_not_a_crash(
    client, mock_vercel
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "deployment already finished"}})

    mock_vercel(handler)

    _, payload = call_tool(client, "vercel_cancel_deployment", {"deployment_id": "dpl_done"})
    text = tool_result_text(payload)
    body = json.loads(text)
    assert body["error"]["code"] == "invalid_argument"

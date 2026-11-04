# vercel-mcp

MCP server that gives an MCP-compatible AI client (Claude, ChatGPT, Cursor, or
any other MCP client via the MSPbots Agent platform) access to a tenant's
[Vercel](https://vercel.com) account: projects, deployments, custom domains,
DNS records, and environment variables.

- **Transport**: MCP Streamable HTTP (`POST /mcp`), stateless — no session
  stickiness, no local persistent state.
- **Tech stack**: Python 3.12, `uv`, [FastMCP](https://gofastmcp.com).
- **License**: Apache-2.0. Copyright MSPbots.ai.

This connector talks to Vercel's public REST API
(<https://vercel.com/docs/rest-api>). It does not fork, mirror, or embed any
third-party code — it is a clean-room implementation against Vercel's
documented endpoints.

---

<div align="center">

## MSPbots Connector

**The MCP Gateway built for MSPs: visible, controlled, and your data stays where it belongs.**

[**Get started at connect.mspbots.ai →**](https://connect.mspbots.ai)

</div>

---

MSPbots Connector gives your AI clients one MCP URL to reach your entire MSP stack (RMM, PSA, documentation, security, finance), and gives you control over who can call which tool and a record of everything that was called.

**Hosted service: [connect.mspbots.ai](https://connect.mspbots.ai)** · Free to use.

### Why Connector

![MSPbots Connector](https://stgoss.mspbots.ai/files/mcp/mspbots-mcp.png)

| | |
|---|---|
| **Visible** | Every tool call is logged: who, which vendor, when. Usage dashboard, CSV export, SIEM streaming. |
| **Controlled** | Role-based, per-tool allowlist. Deny by default. |
| **Protected** | Credentials encrypted per record. AI clients never see your vendor passwords or tokens. |
| **MSP-native** | Built for the MSP stack only: RMM, PSA, documentation, security, finance. |

### Quick start

1. **Sign up** at [connect.mspbots.ai](https://connect.mspbots.ai).
2. **Connect your vendors.** Pick from 150+ connectors and authorize each one on the vendor's own page, or bring your own API keys. No extra vendor accounts needed.
3. **Set access.** Create roles and decide which tools each role may call. Nothing is allowed until you allow it.
4. **Add your MCP URL to your AI client.** Copy the URL from your Connector dashboard into Claude, ChatGPT, Cursor, VS Code, Gemini, Codex, or any MCP-capable client.
5. **Ask your AI to do real work**, and watch every call appear in the audit log.

### Features

**Unified gateway**
- One MCP URL for all your AI clients
- 150+ connectors across the MSP stack
- Custom MCP servers supported, free
- Authorization happens on each vendor's own page; the AI never sees passwords or tokens
- Bring your own credentials: use the vendor API keys you already have
- Multiple accounts per app; connect once, reuse across AI clients
- Tool search: finds the right action for the task
- One sign-in; vendor credentials are injected behind the scenes and OAuth tokens refresh automatically

**Visibility**
- Audit log for every tool call (who, which vendor, when)
- Usage dashboard: call volume, top vendors, error rate, per-user activity
- Export audit logs to CSV, or stream to Loki, Graylog, or LogScale (SIEM)
- Optional recording of tool arguments and result summaries (off by default, enabled per organization)

**Control**
- Per-role, per-tool allowlist, deny by default
- owner / admin / member roles
- SCIM provisioning with Entra ID, Okta, JumpCloud, and Google Workspace

**Security**
- Credentials encrypted one record at a time (AES-256-GCM, per-record key)
- AI clients authenticate with OAuth 2.1 + PKCE
- Vendor responses are scanned for prompt-injection patterns and returned as structured data. This is one layer of defense, not a guarantee against every attack.
- Static egress IP for customer firewall and API allowlisting

### Pricing

**Free.**

Links: [connect.mspbots.ai](https://connect.mspbots.ai) · [mspbots.ai](https://mspbots.ai)

---

## Authentication headers

Every request to `/mcp` must carry these headers. Credentials are never read
from environment variables or config files — only from the request.

| Header | Required | Forwarded to Vercel as | Meaning |
|---|---|---|---|
| `X-Vercel-Access-Token` | Yes | `Authorization: Bearer <token>` | Vercel personal or team access token. Generate one at Vercel dashboard → Account Settings → Tokens. |
| `X-Vercel-Team-Id` | No | `teamId=<value>` query parameter on every call | Scopes all calls to a Vercel team. Omit to use the token owner's personal account. |

Missing `X-Vercel-Access-Token` returns `401 {"error": "missing required header(s)", "required": ["X-Vercel-Access-Token"]}`.

## Tools (19)

| Tool | What it does | Hints |
|---|---|---|
| `vercel_list_projects` | List the tenant's/team's projects | read-only |
| `vercel_get_project` | Get a single project by id or name | read-only |
| `vercel_list_deployments` | List deployments, newest first | read-only |
| `vercel_get_deployment` | Get a single deployment by id or url | read-only |
| `vercel_get_deployment_logs` | Get build/runtime events for a deployment | read-only |
| `vercel_create_deployment` | Start a new deployment from a git ref | write, not idempotent |
| `vercel_cancel_deployment` | Cancel a queued/building deployment | destructive, idempotent |
| `vercel_delete_deployment` | Permanently delete a deployment | destructive, idempotent |
| `vercel_promote_deployment` | Point production at a given deployment (promote or roll back) | idempotent |
| `vercel_list_domains` | List domains in the account/team | read-only |
| `vercel_get_domain` | Get a single domain's configuration | read-only |
| `vercel_add_project_domain` | Attach a custom domain to a project | write |
| `vercel_remove_project_domain` | Detach a custom domain from a project | destructive, idempotent |
| `vercel_list_dns_records` | List DNS records for a domain | read-only |
| `vercel_create_dns_record` | Create a DNS record on a domain | write |
| `vercel_delete_dns_record` | Delete a DNS record from a domain | destructive, idempotent |
| `vercel_list_env_vars` | List env vars (metadata only — never a decrypted value) | read-only |
| `vercel_create_env_var` | Create an env var (never echoes the value back) | write |
| `vercel_delete_env_var` | Delete an env var by id | destructive, idempotent |

**Security note**: `vercel_list_env_vars` and `vercel_create_env_var` never
return a decrypted environment-variable value, even though Vercel's API
supports reading one back. This connector does not expose that capability at
all (see `docs/tickets/PRD-21334.md` "Decisions made by DEV01").

## Error envelope

Every tool returns either its result, or this structured error on failure
(never an unhandled exception or a raw Vercel passthrough):

```json
{"error": {"code": "not_found", "message": "deployment dpl_xxx not found", "retryable": false}}
```

`code` is one of: `not_configured`, `unauthorized`, `not_found`,
`invalid_argument`, `rate_limited`, `upstream_error`.

## Running locally

```bash
uv sync
uv run python -m vercel_mcp
# Health check:
curl http://127.0.0.1:8080/health
# A tool call (replace the token with a real Vercel personal access token):
curl -X POST http://127.0.0.1:8080/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'X-Vercel-Access-Token: <your token>' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Testing

```bash
uv run pytest
```

Unit tests mock the Vercel API (no real account needed). Tests covering
AC1-AC3, AC5-AC7, AC9, and the team-scoping half of AC11 need a real Vercel
account/project and are tracked as manual cases in
`docs/tickets/PRD-21334.ac.json`.

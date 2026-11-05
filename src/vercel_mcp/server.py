"""FastMCP application factory for the Vercel connector.

Builds a single Starlette app (not a mounted sub-app) so the Streamable
HTTP session manager's lifespan is wired correctly without the
Mount()-drops-lifespan pitfall (SOP §7): `GET /health` and `POST /mcp` are
both routes on the same top-level app `fastmcp.http_app()` returns.
"""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from vercel_mcp.middleware import CredentialsMiddleware
from vercel_mcp.tools import deployments, dns, domains, env, projects

MCP_PATH = "/mcp"

INSTRUCTIONS = (
    "Manage a tenant's Vercel account: inspect and operate on projects, "
    "deployments, custom domains, DNS records, and environment variables. "
    "Typical flow: list_projects, then list_deployments for a project, then "
    "create_deployment / promote_deployment / cancel_deployment to ship or "
    "roll back a change; manage domains and DNS once a deployment is live; "
    "manage environment variables without ever reading a decrypted value "
    "back. Every call is scoped to the token's personal account unless a "
    "team id header is also present."
)


def create_mcp() -> FastMCP:
    mcp: FastMCP = FastMCP(name="vercel-mcp", instructions=INSTRUCTIONS)
    projects.register(mcp)
    deployments.register(mcp)
    domains.register(mcp)
    dns.register(mcp)
    env.register(mcp)
    return mcp


async def health(_: Request) -> JSONResponse:
    # Pure local probe (AC13): never calls api.vercel.com, so a Vercel
    # outage never flaps the container's health status.
    return JSONResponse({"status": "ok"})


def create_app() -> Starlette:
    mcp = create_mcp()
    # `FastMCP.http_app()` does not forward a `routes` kwarg to the app it
    # builds, so `/health` is added on an outer Starlette app instead. The
    # outer app's `lifespan` is explicitly set to the MCP app's own lifespan
    # (`mcp_app.lifespan`) — `Mount()` alone does NOT run a sub-app's
    # lifespan, which otherwise surfaces as "/mcp" failing with "Task group
    # is not initialized" while "/health" still returns 200 (SOP §7).
    mcp_app = mcp.http_app(
        path=MCP_PATH,
        middleware=[Middleware(CredentialsMiddleware, mcp_path=MCP_PATH)],
        stateless_http=True,
    )
    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount("/", app=mcp_app),
        ],
        lifespan=mcp_app.lifespan,
    )

"""Entry point: run the Vercel MCP service over Streamable HTTP."""

from __future__ import annotations

import uvicorn

from vercel_mcp.server import create_app
from vercel_mcp.settings import settings


def main() -> None:
    app = create_app()
    uvicorn.run(app, host=settings.mcp_http_host, port=settings.mcp_http_port)


if __name__ == "__main__":
    main()

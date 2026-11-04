"""Non-credential runtime configuration.

Credentials are never read from environment variables or config files — they
are supplied per request via HTTP headers (see middleware.py). This module
only carries transport-level settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, tolerant of unknown environment variables.

    `extra="ignore"` is required: the shared container runtime injects
    environment variables this project does not declare, and strict parsing
    would crash the process on startup.
    """

    model_config = SettingsConfigDict(extra="ignore")

    mcp_http_host: str = "0.0.0.0"
    mcp_http_port: int = 8080

    # Vercel's public REST API has a single base URL; no self-hosted variant
    # exists, so this is a constant rather than a per-tenant header value.
    vercel_api_base_url: str = "https://api.vercel.com"


settings = Settings()

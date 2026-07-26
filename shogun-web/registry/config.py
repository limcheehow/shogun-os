"""Configuration for the Shogun OS central registry service."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service
    host: str = Field(default="0.0.0.0", description="Bind address")
    port: int = Field(default=9000, description="Listen port")
    log_level: str = Field(default="info")
    environment: str = Field(default="production")

    # Public domain (tenants get {subdomain}.{registry_domain})
    registry_domain: str = Field(
        default="shogun-os.ai",
        description="Apex domain for tenant subdomains",
    )

    # Auth
    admin_api_key: str = Field(
        default="change-me-admin-key",
        description="Bearer token required for admin endpoints",
    )
    registration_token: Optional[str] = Field(
        default=None,
        description="Optional shared secret required on /api/register",
    )

    # Database
    database_path: str = Field(
        default="/var/lib/shogun-registry/registry.db",
        description="SQLite database file path",
    )

    # Proxy / health
    proxy_timeout_seconds: float = Field(default=60.0)
    websocket_timeout_seconds: float = Field(default=300.0)
    health_check_interval_seconds: int = Field(default=30)
    heartbeat_stale_seconds: int = Field(
        default=120,
        description="Mark tenant offline if no heartbeat within this window",
    )
    backend_connect_timeout_seconds: float = Field(default=5.0)

    # Cloudflare (optional tunnel management)
    cloudflare_api_token: Optional[str] = Field(default=None)
    cloudflare_account_id: Optional[str] = Field(default=None)
    cloudflare_zone_id: Optional[str] = Field(default=None)
    cloudflare_api_base: str = Field(
        default="https://api.cloudflare.com/client/v4"
    )
    enable_tunnel_provisioning: bool = Field(
        default=False,
        description="If true, create CF tunnels/DNS on register when credentials set",
    )
    allow_preferred_subdomain: bool = Field(
        default=False,
        description=(
            "If false (default), ignore preferred_subdomain on /api/register and "
            "always assign a random adjective-noun-NN slug. Vanity names are "
            "admin-only product escape hatches — customers never pick URLs."
        ),
    )
    default_create_tunnel: bool = Field(
        default=True,
        description=(
            "When tunnel provisioning is enabled, create a per-tenant tunnel "
            "unless the register payload explicitly sets create_tunnel=false."
        ),
    )

    # Public install bootstrap (seamless install.sh — no shared secret for customers)
    enable_public_bootstrap: bool = Field(
        default=True,
        description=(
            "If true, POST /api/install/bootstrap issues short-lived single-use "
            "install tickets so installers never need REGISTRATION_TOKEN."
        ),
    )
    bootstrap_ticket_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Lifetime of a bootstrap install ticket (default 1h)",
    )
    bootstrap_rate_limit_per_ip: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Max bootstrap tickets per client IP per hour",
    )
    # Local dev convenience
    allow_insecure_local_db: bool = Field(
        default=False,
        description="If true and DB path parent missing, fall back to ./data/registry.db",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    db_path = Path(settings.database_path)
    parent = db_path.parent
    can_use = True
    try:
        parent.mkdir(parents=True, exist_ok=True)
        if not os.access(parent, os.W_OK):
            can_use = False
    except OSError:
        can_use = False

    if not can_use:
        # Production path not writable — fall back to local data dir
        local = Path(__file__).resolve().parent / "data" / "registry.db"
        local.parent.mkdir(parents=True, exist_ok=True)
        object.__setattr__(settings, "database_path", str(local))
        object.__setattr__(settings, "allow_insecure_local_db", True)
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()

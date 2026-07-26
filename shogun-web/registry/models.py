"""Pydantic and DB row models for the Shogun registry."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class TenantStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DRAINING = "draining"


class TunnelStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"
    DELETED = "deleted"


# ---------------------------------------------------------------------------
# Domain models (API + internal)
# ---------------------------------------------------------------------------


class Tenant(BaseModel):
    """A registered shogun-web tenant backend."""

    id: str
    subdomain: str
    host: str
    port: int
    status: TenantStatus = TenantStatus.ONLINE
    last_seen: datetime
    created_at: datetime
    weight: int = Field(default=100, description="Load-balancing weight")
    instance_id: Optional[str] = Field(
        default=None,
        description="Optional unique instance id when a tenant has multiple backends",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def ws_base_url(self) -> str:
        return f"ws://{self.host}:{self.port}"


class Tunnel(BaseModel):
    """Optional Cloudflare Tunnel mapping for a tenant."""

    id: str
    tenant_id: str
    cloudflare_tunnel_id: str
    status: TunnelStatus = TunnelStatus.PENDING
    created_at: datetime
    dns_record_id: Optional[str] = None
    tunnel_token: Optional[str] = None
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Payload from a tenant shogun-web instance on startup."""

    host: str = Field(..., description="Reachable host/IP of this tenant backend")
    port: int = Field(..., ge=1, le=65535)
    preferred_subdomain: Optional[str] = Field(
        default=None,
        description=(
            "Optional vanity slug. Ignored unless registry "
            "ALLOW_PREFERRED_SUBDOMAIN=true. Product default is random assignment."
        ),
    )
    instance_id: Optional[str] = Field(
        default=None,
        description="Stable instance id for multi-backend tenants",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Re-register an existing tenant id (same subdomain)",
    )
    weight: int = Field(default=100, ge=1, le=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    create_tunnel: Optional[bool] = Field(
        default=None,
        description=(
            "Request Cloudflare tunnel provisioning. None = use registry "
            "DEFAULT_CREATE_TUNNEL when ENABLE_TUNNEL_PROVISIONING is on."
        ),
    )
    registration_token: Optional[str] = None

    @field_validator("host")
    @classmethod
    def host_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("host must not be empty")
        return v

    @field_validator("preferred_subdomain")
    @classmethod
    def normalize_subdomain(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        slug = v.strip().lower().replace("_", "-")
        if not slug or not all(c.isalnum() or c == "-" for c in slug):
            raise ValueError("preferred_subdomain must be alphanumeric/hyphen")
        return slug


class RegisterResponse(BaseModel):
    tenant_id: str
    subdomain: str
    public_url: str
    status: TenantStatus
    tunnel: Optional[Tunnel] = None
    message: str = "registered"


class BootstrapRequest(BaseModel):
    """Public installer handshake — no shared registration secret required."""

    email: Optional[str] = Field(
        default=None,
        description="Optional contact email (abuse / support correlation)",
    )
    display_name: Optional[str] = Field(default=None, max_length=200)
    installer_version: Optional[str] = Field(default=None, max_length=64)


class BootstrapResponse(BaseModel):
    install_token: str = Field(description="Single-use token for POST /api/register")
    expires_at: str
    expires_in_seconds: int
    registry_url: str = Field(
        description="Base URL installers should use (e.g. https://registry.shogun-os.ai)"
    )
    domain: str = Field(description="Tenant domain suffix, e.g. shogun-os.ai")
    message: str = "ok"


class HeartbeatRequest(BaseModel):
    tenant_id: str
    instance_id: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    status: TenantStatus = TenantStatus.ONLINE
    metadata: Optional[dict[str, Any]] = None


class HeartbeatResponse(BaseModel):
    ok: bool = True
    tenant_id: str
    status: TenantStatus
    last_seen: datetime


class TenantListResponse(BaseModel):
    tenants: list[Tenant]
    count: int


class HealthResponse(BaseModel):
    status: str
    service: str = "shogun-registry"
    version: str = "1.0.0"
    tenants_online: int = 0
    tenants_total: int = 0
    database: str = "ok"


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None

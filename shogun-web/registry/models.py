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
        description="Optional preferred slug; assigned only if free",
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
    create_tunnel: bool = Field(
        default=False,
        description="Request Cloudflare tunnel provisioning if enabled",
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

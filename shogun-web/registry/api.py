"""Registry HTTP API: register, heartbeat, admin tenant management."""

from __future__ import annotations

import logging
import random
import re
import secrets
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from cloudflare import CloudflareClient, CloudflareError
from config import Settings, get_settings
from database import Database
from models import (
    HeartbeatRequest,
    HeartbeatResponse,
    HealthResponse,
    RegisterRequest,
    RegisterResponse,
    Tenant,
    TenantListResponse,
    TenantStatus,
    Tunnel,
    TunnelStatus,
)

logger = logging.getLogger("shogun.registry.api")

# adjective-noun-NN subdomain wordlists
ADJECTIVES = [
    "kura",
    "swift",
    "bright",
    "calm",
    "bold",
    "quiet",
    "noble",
    "clever",
    "steady",
    "vivid",
    "silent",
    "golden",
    "iron",
    "azure",
    "crimson",
    "ember",
    "frost",
    "jade",
    "lunar",
    "solar",
    "obsidian",
    "silver",
    "copper",
    "amber",
    "cedar",
    "maple",
    "ocean",
    "ridge",
    "stone",
    "velvet",
    "zen",
    "prime",
    "rapid",
    "hidden",
    "loyal",
    "fierce",
    "gentle",
    "lucky",
    "honest",
    "patient",
]

NOUNS = [
    "zen",
    "crane",
    "fox",
    "wolf",
    "hawk",
    "river",
    "peak",
    "grove",
    "blade",
    "forge",
    "harbor",
    "lantern",
    "oracle",
    "portal",
    "shard",
    "temple",
    "tower",
    "valley",
    "wave",
    "wind",
    "anchor",
    "beacon",
    "castle",
    "dragon",
    "falcon",
    "garden",
    "herald",
    "island",
    "keeper",
    "lotus",
    "mirror",
    "nexus",
    "onyx",
    "phoenix",
    "quarry",
    "raven",
    "samurai",
    "tiger",
    "umbra",
    "voyage",
]

_SUBDOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def generate_subdomain(db: Database, *, max_attempts: int = 40) -> str:
    """Assign `adjective-noun-NN` that is not already taken."""
    for _ in range(max_attempts):
        adj = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        num = secrets.randbelow(90) + 10  # 10–99
        candidate = f"{adj}-{noun}-{num}"
        if adj == noun:
            continue
        if not db.subdomain_exists(candidate):
            return candidate
    # Extremely unlikely fallback
    suffix = secrets.token_hex(3)
    return f"tenant-{suffix}"


def validate_subdomain(slug: str) -> bool:
    return bool(_SUBDOMAIN_RE.match(slug)) and ".." not in slug


class RegistryAPI:
    """Holds dependencies shared by route handlers."""

    def __init__(
        self,
        db: Database,
        settings: Optional[Settings] = None,
        cf: Optional[CloudflareClient] = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.cf = cf or CloudflareClient(self.settings)
        self.router = APIRouter(prefix="/api", tags=["registry"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/register",
            self.register,
            methods=["POST"],
            response_model=RegisterResponse,
        )
        self.router.add_api_route(
            "/heartbeat",
            self.heartbeat,
            methods=["POST"],
            response_model=HeartbeatResponse,
        )
        self.router.add_api_route(
            "/tenants",
            self.list_tenants,
            methods=["GET"],
            response_model=TenantListResponse,
        )
        self.router.add_api_route(
            "/tenants/{tenant_id}",
            self.get_tenant,
            methods=["GET"],
            response_model=Tenant,
        )
        self.router.add_api_route(
            "/tenants/{tenant_id}",
            self.delete_tenant,
            methods=["DELETE"],
        )
        self.router.add_api_route(
            "/health",
            self.health,
            methods=["GET"],
            response_model=HealthResponse,
        )
        self.router.add_api_route(
            "/tunnels",
            self.list_tunnels,
            methods=["GET"],
        )

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _require_admin(
        self,
        authorization: Optional[str] = None,
        x_api_key: Optional[str] = None,
    ) -> None:
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        elif x_api_key:
            token = x_api_key.strip()
        expected = self.settings.admin_api_key
        if not expected or token != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing admin credentials",
            )

    def _check_registration_token(self, provided: Optional[str]) -> None:
        expected = self.settings.registration_token
        if not expected:
            return
        if not provided or not secrets.compare_digest(provided, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid registration token",
            )

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    async def register(self, body: RegisterRequest) -> RegisterResponse:
        self._check_registration_token(body.registration_token)

        # Re-register path: keep subdomain
        if body.tenant_id:
            existing = self.db.get_tenant(body.tenant_id)
            if existing:
                tenant = self.db.upsert_tenant_instance(
                    subdomain=existing.subdomain,
                    host=body.host,
                    port=body.port,
                    tenant_id=existing.id,
                    instance_id=body.instance_id,
                    weight=body.weight,
                    metadata=body.metadata,
                )
                public = f"https://{tenant.subdomain}.{self.settings.registry_domain}"
                tunnels = self.db.list_tunnels_for_tenant(tenant.id)
                return RegisterResponse(
                    tenant_id=tenant.id,
                    subdomain=tenant.subdomain,
                    public_url=public,
                    status=tenant.status,
                    tunnel=tunnels[0] if tunnels else None,
                    message="re-registered",
                )

        subdomain: Optional[str] = None
        if body.preferred_subdomain:
            if not validate_subdomain(body.preferred_subdomain):
                raise HTTPException(
                    status_code=400, detail="Invalid preferred_subdomain"
                )
            if body.instance_id and self.db.subdomain_exists(body.preferred_subdomain):
                # Multi-instance under existing subdomain is allowed
                subdomain = body.preferred_subdomain
            elif not self.db.subdomain_exists(body.preferred_subdomain):
                subdomain = body.preferred_subdomain
            else:
                # Preferred taken and not multi-instance attach
                logger.info(
                    "Preferred subdomain %s taken; generating new",
                    body.preferred_subdomain,
                )

        if not subdomain:
            subdomain = generate_subdomain(self.db)

        tenant = self.db.upsert_tenant_instance(
            subdomain=subdomain,
            host=body.host,
            port=body.port,
            instance_id=body.instance_id,
            weight=body.weight,
            metadata=body.metadata,
        )

        tunnel_model: Optional[Tunnel] = None
        if body.create_tunnel and self.settings.enable_tunnel_provisioning:
            tunnel_model = await self._provision_tunnel(tenant)

        public = f"https://{tenant.subdomain}.{self.settings.registry_domain}"
        logger.info(
            "Registered tenant id=%s subdomain=%s -> %s:%s",
            tenant.id,
            tenant.subdomain,
            tenant.host,
            tenant.port,
        )
        return RegisterResponse(
            tenant_id=tenant.id,
            subdomain=tenant.subdomain,
            public_url=public,
            status=tenant.status,
            tunnel=tunnel_model,
            message="registered",
        )

    async def _provision_tunnel(self, tenant: Tenant) -> Optional[Tunnel]:
        if not self.cf.configured:
            logger.warning("Tunnel requested but Cloudflare is not configured")
            return None
        try:
            result = await self.cf.ensure_tenant_tunnel(
                subdomain=tenant.subdomain,
                domain=self.settings.registry_domain,
                local_service=f"http://{tenant.host}:{tenant.port}",
            )
            tunnel = self.db.create_tunnel(
                tenant_id=tenant.id,
                cloudflare_tunnel_id=result["tunnel_id"],
                status=TunnelStatus.ACTIVE,
                dns_record_id=result.get("dns_record_id"),
                tunnel_token=result.get("token") or result.get("tunnel_secret"),
                name=result.get("name"),
            )
            return tunnel
        except CloudflareError as exc:
            logger.error("Cloudflare provisioning failed: %s", exc)
            # Soft-fail: tenant still registered
            return None

    async def heartbeat(self, body: HeartbeatRequest) -> HeartbeatResponse:
        tenant = self.db.get_tenant(body.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # If instance_id provided, ensure it matches or update correct row
        if body.instance_id and tenant.instance_id and body.instance_id != tenant.instance_id:
            alt = self.db.get_tenant_by_subdomain_instance(
                tenant.subdomain, body.instance_id
            )
            if alt:
                tenant = alt
            else:
                raise HTTPException(
                    status_code=404, detail="Tenant instance not found"
                )

        updated = self.db.heartbeat(
            tenant.id,
            host=body.host,
            port=body.port,
            status=body.status,
            metadata=body.metadata,
        )
        return HeartbeatResponse(
            ok=True,
            tenant_id=updated.id,
            status=updated.status,
            last_seen=updated.last_seen,
        )

    async def list_tenants(
        self,
        authorization: Annotated[Optional[str], Header()] = None,
        x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
        status_filter: Optional[TenantStatus] = None,
    ) -> TenantListResponse:
        self._require_admin(authorization, x_api_key)
        tenants = self.db.list_tenants(status=status_filter)
        return TenantListResponse(tenants=tenants, count=len(tenants))

    async def get_tenant(
        self,
        tenant_id: str,
        authorization: Annotated[Optional[str], Header()] = None,
        x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    ) -> Tenant:
        self._require_admin(authorization, x_api_key)
        tenant = self.db.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant

    async def delete_tenant(
        self,
        tenant_id: str,
        authorization: Annotated[Optional[str], Header()] = None,
        x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    ) -> dict:
        self._require_admin(authorization, x_api_key)
        tenant = self.db.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Best-effort tunnel cleanup
        for tun in self.db.list_tunnels_for_tenant(tenant_id):
            if self.cf.configured:
                try:
                    if tun.dns_record_id:
                        await self.cf.delete_dns_record(tun.dns_record_id)
                    await self.cf.delete_tunnel(tun.cloudflare_tunnel_id)
                except CloudflareError as exc:
                    logger.warning("Tunnel cleanup failed: %s", exc)
            self.db.delete_tunnel(tun.id)

        self.db.delete_tenant(tenant_id)
        logger.info("Deregistered tenant id=%s subdomain=%s", tenant_id, tenant.subdomain)
        return {"ok": True, "deleted": tenant_id, "subdomain": tenant.subdomain}

    async def health(self) -> HealthResponse:
        try:
            online, total = self.db.counts()
            db_status = "ok"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Health DB check failed: %s", exc)
            online, total = 0, 0
            db_status = "error"
        return HealthResponse(
            status="ok" if db_status == "ok" else "degraded",
            tenants_online=online,
            tenants_total=total,
            database=db_status,
        )

    async def list_tunnels(
        self,
        authorization: Annotated[Optional[str], Header()] = None,
        x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    ) -> dict:
        self._require_admin(authorization, x_api_key)
        local = self.db.list_tunnels()
        remote: list = []
        if self.cf.configured:
            try:
                remote = await self.cf.list_tunnels()
            except CloudflareError as exc:
                logger.warning("list remote tunnels failed: %s", exc)
        return {
            "local": [t.model_dump(mode="json") for t in local],
            "cloudflare": remote,
        }


def build_api_router(
    db: Database,
    settings: Optional[Settings] = None,
    cf: Optional[CloudflareClient] = None,
) -> APIRouter:
    return RegistryAPI(db, settings=settings, cf=cf).router

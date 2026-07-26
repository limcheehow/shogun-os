"""Registry HTTP API: register, heartbeat, admin tenant management."""

from __future__ import annotations

import logging
import random
import re
import secrets
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from cloudflare import CloudflareClient, CloudflareError
from config import Settings, get_settings
from database import Database
from datetime import datetime, timedelta, timezone


from models import (
    BootstrapRequest,
    BootstrapResponse,
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
            "/install/bootstrap",
            self.install_bootstrap,
            methods=["POST"],
            response_model=BootstrapResponse,
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

    def _accept_registration_credential(self, provided: Optional[str]) -> Optional[str]:
        """
        Validate register auth.

        Accepts either:
          1) Legacy operator REGISTRATION_TOKEN (shared secret), or
          2) A single-use public install ticket from /api/install/bootstrap

        Returns ticket token string if a bootstrap ticket was used (to redeem later),
        else None.
        """
        provided = (provided or "").strip()
        expected = (self.settings.registration_token or "").strip()

        # 1) Shared operator token
        if expected and provided and secrets.compare_digest(provided, expected):
            return None

        # 2) Bootstrap install ticket
        if provided:
            ticket = self.db.get_install_ticket(provided)
            if ticket and ticket.get("redeemed_at") is None:
                exp = ticket["expires_at"]
                now = datetime.now(timezone.utc)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp >= now:
                    return provided

        # 3) Open registration when no shared token configured and bootstrap off
        if not expected and not self.settings.enable_public_bootstrap:
            return None
        if not expected and self.settings.enable_public_bootstrap and not provided:
            # Require a ticket when bootstrap is the public path
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing install ticket — call POST /api/install/bootstrap first",
            )
        if expected and not provided:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing registration credentials — installer should bootstrap",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired registration credentials",
        )

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    async def install_bootstrap(
        self,
        body: BootstrapRequest,
        request: Request,
    ) -> BootstrapResponse:
        """Public: issue a short-lived single-use install ticket."""
        if not self.settings.enable_public_bootstrap:
            raise HTTPException(status_code=403, detail="Public bootstrap disabled")

        client_ip = None
        if request is not None:
            # Prefer first X-Forwarded-For hop (Cloudflare / proxy)
            xff = request.headers.get("cf-connecting-ip") or request.headers.get(
                "x-forwarded-for"
            )
            if xff:
                client_ip = xff.split(",")[0].strip()
            elif request.client:
                client_ip = request.client.host

        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=1)
        since_iso = since.isoformat()
        count = self.db.count_recent_tickets(client_ip or "", since_iso)
        if count >= self.settings.bootstrap_rate_limit_per_ip:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bootstrap rate limit exceeded — try again later",
            )

        ttl = int(self.settings.bootstrap_ticket_ttl_seconds)
        expires = now + timedelta(seconds=ttl)
        token = "inst_" + secrets.token_urlsafe(32)
        self.db.create_install_ticket(
            token=token,
            expires_at=expires,
            client_ip=client_ip,
            email=body.email,
            metadata={
                "display_name": body.display_name,
                "installer_version": body.installer_version,
            },
        )
        domain = self.settings.registry_domain
        registry_url = f"https://registry.{domain}"
        logger.info(
            "Issued install ticket ip=%s email=%s ttl=%ss",
            client_ip,
            body.email,
            ttl,
        )
        return BootstrapResponse(
            install_token=token,
            expires_at=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            expires_in_seconds=ttl,
            registry_url=registry_url,
            domain=domain,
            message="ok",
        )

    async def register(self, body: RegisterRequest) -> RegisterResponse:
        ticket_to_redeem = self._accept_registration_credential(body.registration_token)

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
                if ticket_to_redeem:
                    self.db.redeem_install_ticket(ticket_to_redeem, tenant.id)
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
        # Product default: always random. Vanity / preferred only when
        # ALLOW_PREFERRED_SUBDOMAIN=true (admin / paid escape hatch).
        if body.preferred_subdomain and self.settings.allow_preferred_subdomain:
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
                logger.info(
                    "Preferred subdomain %s taken; generating random",
                    body.preferred_subdomain,
                )
        elif body.preferred_subdomain and not self.settings.allow_preferred_subdomain:
            logger.info(
                "Ignoring preferred_subdomain=%s (allow_preferred_subdomain=false)",
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

        if ticket_to_redeem:
            ok = self.db.redeem_install_ticket(ticket_to_redeem, tenant.id)
            if not ok:
                # Extremely unlikely race (double-submit). Reject to avoid free multi-tenant.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Install ticket already used or expired",
                )

        tunnel_model: Optional[Tunnel] = None
        want_tunnel = False
        if self.settings.enable_tunnel_provisioning:
            if body.create_tunnel is True:
                want_tunnel = True
            elif body.create_tunnel is False:
                want_tunnel = False
            else:
                want_tunnel = bool(self.settings.default_create_tunnel)
        if want_tunnel:
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
            # cloudflared runs on the tenant machine; always target localhost there.
            result = await self.cf.ensure_tenant_tunnel(
                subdomain=tenant.subdomain,
                domain=self.settings.registry_domain,
                local_service=f"http://127.0.0.1:{tenant.port}",
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

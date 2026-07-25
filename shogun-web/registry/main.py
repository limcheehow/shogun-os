"""
Shogun OS central registry service.

Runs on a VPS behind a Cloudflare Tunnel wildcard (`*.shogun-os.ai`).
- Registry API under the apex / known hosts (register, heartbeat, admin).
- All other subdomain traffic is reverse-proxied to the tenant backend.
"""

from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from typing import Callable, Optional

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from api import build_api_router
from cloudflare import CloudflareClient
from config import Settings, get_settings
from database import Database
from router import TenantRouter

logger = logging.getLogger("shogun.registry")

VERSION = "1.0.0"

# Hosts that serve the registry API itself (not proxied)
_APEX_NAMES = {"www", "registry", "api", "admin", ""}


def extract_subdomain(host: str, registry_domain: str) -> Optional[str]:
    """
    Extract tenant subdomain from Host header.

    Examples (registry_domain=shogun-os.ai):
      kura-zen-42.shogun-os.ai → kura-zen-42
      shogun-os.ai             → None (apex)
      localhost:9000           → None
    """
    if not host:
        return None
    host = host.split(":")[0].strip().lower()
    domain = registry_domain.strip().lower()

    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return None
    if host == domain or host == f"www.{domain}":
        return None

    suffix = f".{domain}"
    if host.endswith(suffix):
        sub = host[: -len(suffix)]
        if not sub or "." in sub:
            # multi-level or empty — treat first label only if single extra label intent
            # reject nested like a.b.shogun-os.ai for safety
            if "." in sub:
                return None
            return None
        if sub in _APEX_NAMES:
            return None
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", sub):
            return None
        return sub

    # Dev: support host like tenant.localhost
    if host.endswith(".localhost"):
        sub = host[: -len(".localhost")]
        if sub and "." not in sub:
            return sub

    return None


class SubdomainMiddleware(BaseHTTPMiddleware):
    """Attach `request.state.subdomain` from the Host header."""

    def __init__(self, app: ASGIApp, registry_domain: str) -> None:
        super().__init__(app)
        self.registry_domain = registry_domain

    async def dispatch(self, request: Request, call_next: Callable):
        host = request.headers.get("host", "")
        request.state.subdomain = extract_subdomain(host, self.registry_domain)
        request.state.raw_host = host
        return await call_next(request)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()

    # Configure logging once
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    db = Database(settings.database_path)
    cf = CloudflareClient(settings)
    tenant_router = TenantRouter(db, settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = db
        app.state.settings = settings
        app.state.cf = cf
        app.state.tenant_router = tenant_router
        await tenant_router.startup()
        logger.info(
            "Shogun registry listening domain=%s db=%s",
            settings.registry_domain,
            settings.database_path,
        )
        yield
        await tenant_router.shutdown()

    app = FastAPI(
        title="Shogun OS Registry",
        description="Central routing and tenant registry for Shogun OS web portal",
        version=VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SubdomainMiddleware, registry_domain=settings.registry_domain)

    # Registry API always available on apex / any host under /api/*
    app.include_router(build_api_router(db, settings=settings, cf=cf))

    @app.get("/health")
    @app.get("/api/healthz")
    async def root_health():
        online, total = db.counts()
        return {
            "status": "ok",
            "service": "shogun-registry",
            "version": VERSION,
            "tenants_online": online,
            "tenants_total": total,
        }

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        include_in_schema=False,
    )
    async def proxy_catch_all(request: Request, path: str) -> Response:
        """
        Proxy non-API traffic when Host carries a tenant subdomain.

        API routes registered above take precedence for exact paths on the
        same app; this catch-all handles tenant portal traffic.
        """
        # Never proxy if path is clearly API (safety if routing order changes)
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)

        subdomain = getattr(request.state, "subdomain", None)
        if not subdomain:
            return JSONResponse(
                {
                    "service": "shogun-registry",
                    "version": VERSION,
                    "message": (
                        "Shogun OS central registry. "
                        "Tenant portals are at https://{subdomain}."
                        f"{settings.registry_domain}/"
                    ),
                    "endpoints": {
                        "register": "POST /api/register",
                        "heartbeat": "POST /api/heartbeat",
                        "health": "GET /api/health",
                        "tenants": "GET /api/tenants (admin)",
                    },
                }
            )

        return await tenant_router.proxy_http(request, subdomain)

    @app.websocket("/{path:path}")
    async def websocket_proxy(websocket: WebSocket, path: str) -> None:
        host = websocket.headers.get("host", "")
        subdomain = extract_subdomain(host, settings.registry_domain)
        if not subdomain:
            await websocket.close(code=4400, reason="No tenant subdomain in Host")
            return
        await tenant_router.proxy_websocket(websocket, subdomain)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()

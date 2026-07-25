"""HTTP and WebSocket reverse proxy to tenant backends."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional
from urllib.parse import urljoin

import httpx
from fastapi import Request, Response, WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse
from starlette.websockets import WebSocketState

from config import Settings, get_settings
from database import Database
from models import Tenant, TenantStatus

logger = logging.getLogger("shogun.registry.router")

# Hop-by-hop headers must not be forwarded (RFC 7230)
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


class TenantRouter:
    """Select backend and proxy HTTP / WebSocket traffic."""

    def __init__(self, db: Database, settings: Optional[Settings] = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._rr_counters: dict[str, int] = {}
        self._health_task: Optional[asyncio.Task[None]] = None

    async def startup(self) -> None:
        timeout = httpx.Timeout(
            self.settings.proxy_timeout_seconds,
            connect=self.settings.backend_connect_timeout_seconds,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        )
        self._health_task = asyncio.create_task(self._health_loop())
        logger.info("TenantRouter started")

    async def shutdown(self) -> None:
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("TenantRouter stopped")

    # ------------------------------------------------------------------
    # Backend selection / load balancing
    # ------------------------------------------------------------------

    def select_backend(self, subdomain: str) -> Optional[Tenant]:
        """Weighted random among online instances; round-robin fallback."""
        online = self.db.list_online_by_subdomain(subdomain)
        if not online:
            # Try any registered instance even if offline (last chance)
            all_inst = self.db.list_tenants_by_subdomain(subdomain)
            if not all_inst:
                return None
            # Prefer most recently seen
            all_inst.sort(key=lambda t: t.last_seen, reverse=True)
            return all_inst[0]

        total_weight = sum(max(t.weight, 1) for t in online)
        if total_weight <= 0:
            return random.choice(online)

        r = random.uniform(0, total_weight)
        upto = 0.0
        for t in online:
            upto += max(t.weight, 1)
            if r <= upto:
                return t
        return online[-1]

    def select_backend_round_robin(self, subdomain: str) -> Optional[Tenant]:
        online = self.db.list_online_by_subdomain(subdomain)
        if not online:
            return self.select_backend(subdomain)
        idx = self._rr_counters.get(subdomain, 0) % len(online)
        self._rr_counters[subdomain] = idx + 1
        return online[idx]

    # ------------------------------------------------------------------
    # Health checking
    # ------------------------------------------------------------------

    async def _health_loop(self) -> None:
        interval = max(5, self.settings.health_check_interval_seconds)
        while True:
            try:
                await asyncio.sleep(interval)
                await self.check_all_tenants()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("Health loop error")

    async def check_all_tenants(self) -> None:
        stale = self.db.mark_stale_offline(self.settings.heartbeat_stale_seconds)
        if stale:
            logger.info("Marked %s tenants offline due to stale heartbeat", stale)

        tenants = self.db.list_tenants()
        # Deduplicate by host:port to avoid hammering multi-domain aliases
        seen: set[tuple[str, int]] = set()
        for t in tenants:
            key = (t.host, t.port)
            if key in seen:
                continue
            seen.add(key)
            ok = await self.probe_tenant(t)
            desired = TenantStatus.ONLINE if ok else TenantStatus.OFFLINE
            if t.status != desired and (
                # Don't flip online tenants offline solely on probe if heartbeat is fresh
                desired == TenantStatus.ONLINE
                or t.status == TenantStatus.ONLINE
            ):
                if desired == TenantStatus.OFFLINE and ok is False:
                    self.db.set_status(t.id, TenantStatus.OFFLINE)
                    logger.warning(
                        "Tenant %s (%s:%s) unreachable — marked offline",
                        t.subdomain,
                        t.host,
                        t.port,
                    )
                elif desired == TenantStatus.ONLINE:
                    self.db.set_status(t.id, TenantStatus.ONLINE)

    async def probe_tenant(self, tenant: Tenant) -> bool:
        if not self._client:
            return False
        url = f"{tenant.base_url}/api/health"
        alt = f"{tenant.base_url}/health"
        for candidate in (url, alt, tenant.base_url):
            try:
                resp = await self._client.get(candidate)
                if resp.status_code < 500:
                    return True
            except (httpx.HTTPError, httpx.TimeoutException, OSError):
                continue
        return False

    # ------------------------------------------------------------------
    # HTTP proxy
    # ------------------------------------------------------------------

    async def proxy_http(self, request: Request, subdomain: str) -> Response:
        if not self._client:
            return Response("Proxy not ready", status_code=503)

        backend = self.select_backend(subdomain)
        if not backend:
            return Response(
                f"Unknown or unregistered tenant: {subdomain}",
                status_code=404,
                media_type="text/plain",
            )

        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"

        target = urljoin(f"{backend.base_url}/", path.lstrip("/"))
        # urljoin can drop path incorrectly; build explicitly
        target = f"{backend.base_url}{request.url.path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        headers = self._filter_request_headers(request)
        headers["x-forwarded-host"] = request.headers.get("host", "")
        headers["x-forwarded-proto"] = request.headers.get(
            "x-forwarded-proto", request.url.scheme
        )
        headers["x-shogun-subdomain"] = subdomain
        headers["x-shogun-tenant-id"] = backend.id

        body = await request.body()

        try:
            upstream = await self._client.request(
                request.method,
                target,
                headers=headers,
                content=body,
            )
        except httpx.ConnectError:
            self.db.set_status(backend.id, TenantStatus.OFFLINE)
            logger.warning(
                "Connect failed to %s://%s:%s — offline",
                "http",
                backend.host,
                backend.port,
            )
            return Response("Tenant backend unreachable", status_code=502)
        except httpx.TimeoutException:
            return Response("Tenant backend timeout", status_code=504)
        except httpx.HTTPError as exc:
            logger.exception("Proxy error subdomain=%s: %s", subdomain, exc)
            return Response("Bad gateway", status_code=502)

        resp_headers = {
            k: v
            for k, v in upstream.headers.items()
            if k.lower() not in HOP_BY_HOP and k.lower() != "content-encoding"
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=resp_headers,
            media_type=upstream.headers.get("content-type"),
        )

    async def proxy_http_streaming(
        self, request: Request, subdomain: str
    ) -> Response:
        """Optional streaming variant for large responses."""
        if not self._client:
            return Response("Proxy not ready", status_code=503)

        backend = self.select_backend(subdomain)
        if not backend:
            return Response(
                f"Unknown or unregistered tenant: {subdomain}",
                status_code=404,
                media_type="text/plain",
            )

        target = f"{backend.base_url}{request.url.path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        headers = self._filter_request_headers(request)
        headers["x-forwarded-host"] = request.headers.get("host", "")
        headers["x-shogun-subdomain"] = subdomain
        body = await request.body()

        try:
            req = self._client.build_request(
                request.method, target, headers=headers, content=body
            )
            upstream = await self._client.send(req, stream=True)
        except httpx.ConnectError:
            self.db.set_status(backend.id, TenantStatus.OFFLINE)
            return Response("Tenant backend unreachable", status_code=502)
        except httpx.TimeoutException:
            return Response("Tenant backend timeout", status_code=504)
        except httpx.HTTPError:
            return Response("Bad gateway", status_code=502)

        resp_headers = {
            k: v
            for k, v in upstream.headers.items()
            if k.lower() not in HOP_BY_HOP
        }

        async def stream():
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()

        return StreamingResponse(
            stream(),
            status_code=upstream.status_code,
            headers=resp_headers,
            media_type=upstream.headers.get("content-type"),
        )

    def _filter_request_headers(self, request: Request) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in request.headers.items():
            lk = key.lower()
            if lk in HOP_BY_HOP:
                continue
            out[key] = value
        return out

    # ------------------------------------------------------------------
    # WebSocket proxy
    # ------------------------------------------------------------------

    async def proxy_websocket(self, websocket: WebSocket, subdomain: str) -> None:
        backend = self.select_backend(subdomain)
        if not backend:
            await websocket.close(code=4404, reason=f"Unknown tenant: {subdomain}")
            return

        await websocket.accept()

        path = websocket.url.path
        query = websocket.url.query
        ws_url = f"{backend.ws_base_url}{path}"
        if query:
            ws_url = f"{ws_url}?{query}"

        # Forward a subset of headers
        extra_headers: list[tuple[str, str]] = []
        for key in ("authorization", "cookie", "sec-websocket-protocol"):
            val = websocket.headers.get(key)
            if val:
                extra_headers.append((key, val))
        extra_headers.append(("x-shogun-subdomain", subdomain))
        extra_headers.append(("x-shogun-tenant-id", backend.id))

        try:
            import websockets
            from websockets.exceptions import ConnectionClosed
        except ImportError:
            logger.error("websockets package not installed")
            await websocket.close(code=1011, reason="WebSocket proxy unavailable")
            return

        try:
            async with websockets.connect(
                ws_url,
                additional_headers=extra_headers,
                open_timeout=self.settings.backend_connect_timeout_seconds,
                ping_interval=20,
                ping_timeout=20,
                max_size=8 * 1024 * 1024,
            ) as upstream:

                async def client_to_upstream() -> None:
                    try:
                        while True:
                            msg = await websocket.receive()
                            if msg["type"] == "websocket.disconnect":
                                break
                            if msg["type"] != "websocket.receive":
                                continue
                            if "text" in msg and msg["text"] is not None:
                                await upstream.send(msg["text"])
                            elif "bytes" in msg and msg["bytes"] is not None:
                                await upstream.send(msg["bytes"])
                    except WebSocketDisconnect:
                        pass
                    except Exception:  # noqa: BLE001
                        logger.debug("client_to_upstream closed", exc_info=True)

                async def upstream_to_client() -> None:
                    try:
                        async for message in upstream:
                            if websocket.client_state != WebSocketState.CONNECTED:
                                break
                            if isinstance(message, bytes):
                                await websocket.send_bytes(message)
                            else:
                                await websocket.send_text(str(message))
                    except ConnectionClosed:
                        pass
                    except Exception:  # noqa: BLE001
                        logger.debug("upstream_to_client closed", exc_info=True)

                done, pending = await asyncio.wait(
                    [
                        asyncio.create_task(client_to_upstream()),
                        asyncio.create_task(upstream_to_client()),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                for task in done:
                    exc = task.exception()
                    if exc:
                        logger.debug("WS task ended with: %s", exc)

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "WebSocket proxy failed subdomain=%s backend=%s:%s err=%s",
                subdomain,
                backend.host,
                backend.port,
                exc,
            )
            self.db.set_status(backend.id, TenantStatus.OFFLINE)
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1011, reason="Upstream unavailable")
            return

        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()

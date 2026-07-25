"""Cloudflare API client for tunnel + DNS management."""

from __future__ import annotations

import logging
import secrets
from typing import Any, Optional

import httpx

from config import Settings, get_settings

logger = logging.getLogger("shogun.registry.cloudflare")


class CloudflareError(Exception):
    """Raised when the Cloudflare API returns an error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        errors: Optional[list[Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class CloudflareClient:
    """Minimal Cloudflare Zero Trust / DNS client using httpx."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.base = self.settings.cloudflare_api_base.rstrip("/")
        self.token = self.settings.cloudflare_api_token
        self.account_id = self.settings.cloudflare_account_id
        self.zone_id = self.settings.cloudflare_zone_id

    @property
    def configured(self) -> bool:
        return bool(self.token and self.account_id and self.zone_id)

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise CloudflareError("CLOUDFLARE_API_TOKEN is not configured")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method,
                url,
                headers=self._headers(),
                json=json,
                params=params,
            )
        try:
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise CloudflareError(
                f"Invalid JSON from Cloudflare ({resp.status_code})",
                status_code=resp.status_code,
            ) from exc

        if resp.status_code >= 400 or not payload.get("success", False):
            errors = payload.get("errors") or []
            msg = "; ".join(
                e.get("message", str(e)) if isinstance(e, dict) else str(e)
                for e in errors
            ) or f"HTTP {resp.status_code}"
            logger.error("Cloudflare API error: %s path=%s", msg, path)
            raise CloudflareError(msg, status_code=resp.status_code, errors=errors)

        return payload

    # ------------------------------------------------------------------
    # Tunnels (Cloudflare Tunnel / cloudflared)
    # ------------------------------------------------------------------

    async def create_tunnel(
        self,
        name: str,
        *,
        config_src: str = "cloudflare",
    ) -> dict[str, Any]:
        """
        Create a Cloudflare Tunnel.

        Returns result dict with at least: id, name, token (when available).
        """
        if not self.account_id:
            raise CloudflareError("CLOUDFLARE_ACCOUNT_ID is not configured")

        # Secret required by the tunnels API (32+ bytes hex)
        tunnel_secret = secrets.token_hex(32)
        payload = await self._request(
            "POST",
            f"/accounts/{self.account_id}/cfd_tunnel",
            json={
                "name": name,
                "tunnel_secret": tunnel_secret,
                "config_src": config_src,
            },
        )
        result = payload.get("result") or {}
        # token may be present on create responses
        if "token" not in result and tunnel_secret:
            # Some API versions return credentials separately; surface secret for ops
            result = {**result, "tunnel_secret": tunnel_secret}
        logger.info("Created Cloudflare tunnel name=%s id=%s", name, result.get("id"))
        return result

    async def get_tunnel(self, tunnel_id: str) -> dict[str, Any]:
        if not self.account_id:
            raise CloudflareError("CLOUDFLARE_ACCOUNT_ID is not configured")
        payload = await self._request(
            "GET",
            f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}",
        )
        return payload.get("result") or {}

    async def list_tunnels(
        self,
        *,
        name: Optional[str] = None,
        is_deleted: bool = False,
        per_page: int = 50,
    ) -> list[dict[str, Any]]:
        if not self.account_id:
            raise CloudflareError("CLOUDFLARE_ACCOUNT_ID is not configured")
        params: dict[str, Any] = {
            "is_deleted": str(is_deleted).lower(),
            "per_page": per_page,
        }
        if name:
            params["name"] = name
        payload = await self._request(
            "GET",
            f"/accounts/{self.account_id}/cfd_tunnel",
            params=params,
        )
        result = payload.get("result") or []
        return list(result) if isinstance(result, list) else []

    async def delete_tunnel(self, tunnel_id: str) -> bool:
        if not self.account_id:
            raise CloudflareError("CLOUDFLARE_ACCOUNT_ID is not configured")
        await self._request(
            "DELETE",
            f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}",
        )
        logger.info("Deleted Cloudflare tunnel id=%s", tunnel_id)
        return True

    async def configure_tunnel_ingress(
        self,
        tunnel_id: str,
        *,
        hostname: str,
        service: str,
    ) -> dict[str, Any]:
        """Set a simple single-hostname ingress for the tunnel."""
        if not self.account_id:
            raise CloudflareError("CLOUDFLARE_ACCOUNT_ID is not configured")
        payload = await self._request(
            "PUT",
            f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}/configurations",
            json={
                "config": {
                    "ingress": [
                        {"hostname": hostname, "service": service},
                        {"service": "http_status:404"},
                    ]
                }
            },
        )
        return payload.get("result") or {}

    # ------------------------------------------------------------------
    # DNS
    # ------------------------------------------------------------------

    async def create_dns_record(
        self,
        *,
        name: str,
        content: str,
        record_type: str = "CNAME",
        proxied: bool = True,
        ttl: int = 1,
        comment: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a DNS record in the configured zone.

        For tunnels, content is typically `<tunnel_id>.cfargotunnel.com`.
        """
        if not self.zone_id:
            raise CloudflareError("CLOUDFLARE_ZONE_ID is not configured")
        body: dict[str, Any] = {
            "type": record_type,
            "name": name,
            "content": content,
            "proxied": proxied,
            "ttl": ttl,
        }
        if comment:
            body["comment"] = comment
        payload = await self._request(
            "POST",
            f"/zones/{self.zone_id}/dns_records",
            json=body,
        )
        result = payload.get("result") or {}
        logger.info(
            "Created DNS record name=%s type=%s id=%s",
            name,
            record_type,
            result.get("id"),
        )
        return result

    async def delete_dns_record(self, record_id: str) -> bool:
        if not self.zone_id:
            raise CloudflareError("CLOUDFLARE_ZONE_ID is not configured")
        await self._request(
            "DELETE",
            f"/zones/{self.zone_id}/dns_records/{record_id}",
        )
        logger.info("Deleted DNS record id=%s", record_id)
        return True

    async def list_dns_records(
        self,
        *,
        name: Optional[str] = None,
        record_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not self.zone_id:
            raise CloudflareError("CLOUDFLARE_ZONE_ID is not configured")
        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        if record_type:
            params["type"] = record_type
        payload = await self._request(
            "GET",
            f"/zones/{self.zone_id}/dns_records",
            params=params or None,
        )
        result = payload.get("result") or []
        return list(result) if isinstance(result, list) else []

    async def ensure_tenant_tunnel(
        self,
        *,
        subdomain: str,
        domain: str,
        local_service: str = "http://localhost:8000",
    ) -> dict[str, Any]:
        """
        High-level helper: create tunnel + CNAME `{subdomain}.{domain}` → tunnel.

        Returns dict with tunnel_id, dns_record_id, hostname, token/secret.
        """
        hostname = f"{subdomain}.{domain}"
        tunnel_name = f"shogun-{subdomain}"
        tunnel = await self.create_tunnel(tunnel_name)
        tunnel_id = tunnel.get("id")
        if not tunnel_id:
            raise CloudflareError("Tunnel create response missing id")

        try:
            await self.configure_tunnel_ingress(
                tunnel_id,
                hostname=hostname,
                service=local_service,
            )
        except CloudflareError as exc:
            logger.warning("Ingress config failed (non-fatal): %s", exc)

        dns = await self.create_dns_record(
            name=hostname,
            content=f"{tunnel_id}.cfargotunnel.com",
            record_type="CNAME",
            proxied=True,
            comment=f"Shogun OS tenant {subdomain}",
        )
        return {
            "tunnel_id": tunnel_id,
            "dns_record_id": dns.get("id"),
            "hostname": hostname,
            "name": tunnel_name,
            "token": tunnel.get("token"),
            "tunnel_secret": tunnel.get("tunnel_secret"),
            "raw_tunnel": tunnel,
            "raw_dns": dns,
        }

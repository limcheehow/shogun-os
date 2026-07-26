"""Central registry client — bootstrap tickets + public URL claim."""

from __future__ import annotations

import logging
import os
import platform
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import require_admin
from config import SHOGUN_HOME, get_config, load_config, save_config
from database import get_db, get_primary_tenant
from models import Department, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/registry", tags=["registry"])

DEFAULT_REGISTRY = "https://registry.shogun-os.ai"
TUNNEL_TOKEN_PATH = SHOGUN_HOME / "tunnel.token"


class RegisterRequest(BaseModel):
    force: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    create_tunnel: bool = True


class GoLiveRequest(BaseModel):
    """Triggered from onboarding — no customer secrets required."""

    create_tunnel: bool = True
    force: bool = False


def _registry_base() -> str:
    cfg = get_config()
    base = (cfg.registry_url or os.environ.get("SHOGUN_REGISTRY_URL") or DEFAULT_REGISTRY).strip()
    return base.rstrip("/")


def _extract_tunnel_token(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    tun = body.get("tunnel")
    if isinstance(tun, dict):
        for key in ("tunnel_token", "token", "cloudflare_token"):
            val = tun.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    for key in ("tunnel_token", "cloudflare_tunnel_token"):
        val = body.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _persist_tunnel_token(token: str) -> Path:
    SHOGUN_HOME.mkdir(parents=True, exist_ok=True)
    TUNNEL_TOKEN_PATH.write_text(token.strip() + "\n", encoding="utf-8")
    try:
        TUNNEL_TOKEN_PATH.chmod(0o600)
    except OSError:
        pass
    return TUNNEL_TOKEN_PATH


def _try_start_cloudflared(token: str) -> Dict[str, Any]:
    """Best-effort start cloudflared in background if installed."""
    bin_path = None
    for candidate in ("cloudflared", "/usr/local/bin/cloudflared", "/usr/bin/cloudflared"):
        from shutil import which

        found = which(candidate) if candidate == "cloudflared" else (
            candidate if Path(candidate).is_file() else None
        )
        if found:
            bin_path = found
            break
    if not bin_path:
        return {
            "started": False,
            "reason": "cloudflared not installed",
            "hint": "Install cloudflared or re-run installer; token saved for later.",
        }
    log_path = SHOGUN_HOME / "cloudflared.log"
    try:
        # Detached process; token via env-less argv
        with open(log_path, "ab") as logf:
            subprocess.Popen(
                [bin_path, "tunnel", "run", "--token", token],
                stdout=logf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return {"started": True, "binary": bin_path, "log": str(log_path)}
    except OSError as exc:
        return {"started": False, "reason": str(exc), "binary": bin_path}


async def bootstrap_install_ticket(
    *,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Public bootstrap — mint single-use install ticket (no shared secret)."""
    base = _registry_base()
    url = f"{base}/api/install/bootstrap"
    payload = {
        "email": email,
        "display_name": display_name,
        "installer_version": "shogun-web-onboarding",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload)
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        if resp.status_code >= 400:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": body,
                "url": url,
            }
        token = body.get("install_token") if isinstance(body, dict) else None
        if not token:
            return {"ok": False, "error": "no install_token in bootstrap response", "body": body}
        return {
            "ok": True,
            "install_token": token,
            "domain": body.get("domain"),
            "expires_in_seconds": body.get("expires_in_seconds"),
            "registry_url": body.get("registry_url") or base,
            "body": body,
        }


def build_registration_payload(
    db: Session,
    *,
    install_token: Optional[str] = None,
    create_tunnel: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble RegisterRequest for central registry (product schema)."""
    cfg = get_config()
    tenant = get_primary_tenant(db)
    active_depts = list(
        db.execute(
            select(Department).where(
                Department.tenant_id == tenant.id, Department.status == "active"
            )
        ).scalars()
    )
    user_count = db.execute(
        select(func.count()).select_from(User).where(User.tenant_id == tenant.id)
    ).scalar_one()

    meta: Dict[str, Any] = {
        "display_name": tenant.company_name,
        "timezone": tenant.timezone,
        "hostname": socket.gethostname(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "departments": [
            {
                "name": d.name,
                "profile_name": d.profile_name,
                "status": d.status,
                "gateway_port": d.gateway_port,
            }
            for d in active_depts
        ],
        "stats": {
            "user_count": int(user_count or 0),
            "active_departments": len(active_depts),
        },
        "local_url": f"http://127.0.0.1:{cfg.port}",
        "version": "1.0.0",
        "source": "web-onboarding",
    }
    if metadata:
        meta.update(metadata)

    payload: Dict[str, Any] = {
        "host": "127.0.0.1",
        "port": int(cfg.port),
        "create_tunnel": bool(create_tunnel),
        "metadata": meta,
    }

    # Re-register with stable id if we already have a real registry tenant id
    tenant_id = getattr(cfg, "tenant_id", None) or None
    if isinstance(tenant_id, str) and tenant_id and not tenant_id.startswith("pending"):
        payload["tenant_id"] = tenant_id

    # Credential: install ticket preferred; operator key fallback
    token = install_token or cfg.registry_api_key or os.environ.get("SHOGUN_REGISTRY_TOKEN")
    if token:
        payload["registration_token"] = token

    return payload


def apply_registry_identity(db: Session, body: Dict[str, Any]) -> Dict[str, Any]:
    """Persist assigned subdomain / public_url / tenant_id into DB + web.json."""
    cfg = load_config(force_reload=True)
    tenant = get_primary_tenant(db)

    subdomain = body.get("subdomain") or body.get("slug")
    public_url = body.get("public_url")
    tenant_id = body.get("tenant_id") or body.get("id")

    if subdomain:
        tenant.subdomain = str(subdomain)
        cfg.subdomain = str(subdomain)
    if public_url:
        cfg.public_base_url = str(public_url)
        if str(public_url) not in cfg.cors_origins:
            cfg.cors_origins = list(cfg.cors_origins) + [str(public_url)]
    if tenant_id:
        cfg.tenant_id = str(tenant_id)

    if tenant.company_name:
        cfg.company_name = tenant.company_name
    cfg.timezone = tenant.timezone or cfg.timezone

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    save_config(cfg)
    try:
        import json

        path = SHOGUN_HOME / "web.json"
        raw: Dict[str, Any] = {}
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
        if tenant_id:
            raw["tenant_id"] = str(tenant_id)
        if public_url:
            raw["public_url"] = str(public_url)
            raw.setdefault("server", {})
            if isinstance(raw["server"], dict):
                raw["server"]["public_url"] = str(public_url)
        if subdomain:
            raw["subdomain"] = str(subdomain)
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not merge tenant_id into web.json: %s", exc)

    load_config(force_reload=True)
    return {
        "subdomain": tenant.subdomain,
        "public_url": public_url or f"https://{tenant.subdomain}.shogun-os.ai",
        "tenant_id": tenant_id,
        "company_name": tenant.company_name,
    }


async def register_with_central(
    db: Session,
    *,
    force: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    create_tunnel: bool = True,
    install_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Bootstrap (if needed) + register with central registry.

    Customer path never needs a pre-shared REGISTRATION_TOKEN.
    """
    cfg = get_config()
    base = _registry_base()

    # Skip if already live and not forcing
    if (
        not force
        and cfg.subdomain
        and cfg.subdomain not in {"local", "pending", ""}
        and cfg.public_base_url.startswith("https://")
        and "localhost" not in cfg.public_base_url
    ):
        return {
            "ok": True,
            "skipped": True,
            "reason": "already_registered",
            "subdomain": cfg.subdomain,
            "public_url": cfg.public_base_url,
        }

    token = install_token or cfg.registry_api_key or os.environ.get("SHOGUN_REGISTRY_TOKEN")
    boot_meta: Dict[str, Any] = {}
    if not token:
        tenant = get_primary_tenant(db)
        admin_email = None
        admin = db.execute(
            select(User)
            .where(User.tenant_id == tenant.id)
            .order_by(User.id.asc())
            .limit(1)
        ).scalar_one_or_none()
        if admin:
            admin_email = admin.email
        boot = await bootstrap_install_ticket(
            email=admin_email,
            display_name=tenant.company_name,
        )
        boot_meta = boot
        if not boot.get("ok"):
            return {
                "ok": False,
                "stage": "bootstrap",
                "error": boot.get("error") or boot,
                "registry_url": base,
            }
        token = boot["install_token"]

    payload = build_registration_payload(
        db,
        install_token=token,
        create_tunnel=create_tunnel,
        metadata=metadata,
    )
    if force:
        payload["force"] = True

    url = f"{base}/api/register"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:1000]}
            ok = resp.status_code < 400
            if not ok:
                logger.warning("Registry register failed %s: %s", resp.status_code, body)
                return {
                    "ok": False,
                    "stage": "register",
                    "status_code": resp.status_code,
                    "response": body,
                    "registry_url": url,
                    "bootstrap": {k: boot_meta.get(k) for k in ("domain", "expires_in_seconds") if k in boot_meta},
                }

            identity = apply_registry_identity(db, body if isinstance(body, dict) else {})
            tunnel_token = _extract_tunnel_token(body)
            tunnel_info: Dict[str, Any] = {"token_saved": False}
            if tunnel_token:
                path = _persist_tunnel_token(tunnel_token)
                tunnel_info["token_saved"] = True
                tunnel_info["token_path"] = str(path)
                tunnel_info["connector"] = _try_start_cloudflared(tunnel_token)

            return {
                "ok": True,
                "stage": "register",
                "status_code": resp.status_code,
                "response": body,
                "registry_url": url,
                "subdomain": identity.get("subdomain"),
                "public_url": identity.get("public_url"),
                "tenant_id": identity.get("tenant_id"),
                "tunnel": tunnel_info,
                "message": "Your company dashboard is live",
            }
    except httpx.HTTPError as exc:
        logger.warning("Registry unreachable: %s", exc)
        return {
            "ok": False,
            "stage": "register",
            "error": str(exc),
            "registry_url": url,
        }


async def go_live(db: Session, *, create_tunnel: bool = True, force: bool = False) -> Dict[str, Any]:
    """Onboarding entrypoint — claim public URL + start tunnel."""
    result = await register_with_central(db, force=force, create_tunnel=create_tunnel)
    return result


@router.post("/register")
async def register_route(
    body: RegisterRequest,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Manually (re)register this tenant with the central registry."""
    result = await register_with_central(
        db,
        force=body.force,
        metadata=body.metadata,
        create_tunnel=body.create_tunnel,
    )
    if result.get("skipped") and result.get("reason") == "registry_url not configured":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("reason") or "Registry not configured",
        )
    return result


@router.post("/go-live")
async def go_live_route(
    body: GoLiveRequest,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Dummy-proof: bootstrap ticket + register + optional cloudflared."""
    _ = user
    result = await go_live(db, create_tunnel=body.create_tunnel, force=body.force)
    if not result.get("ok") and not result.get("skipped"):
        # Still return 200 with ok:false so UI can show friendly error; use 502 for hard fail
        err = result.get("error") or result.get("response") or "go-live failed"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=err if isinstance(err, str) else str(err)[:500],
        )
    return result


@router.get("/status")
async def registry_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Public-ish status for onboarding / dashboard banner."""
    cfg = get_config()
    tenant = get_primary_tenant(db)
    live = bool(
        cfg.subdomain
        and cfg.subdomain not in {"local", "pending"}
        and cfg.public_base_url.startswith("https://")
    )
    return {
        "live": live,
        "subdomain": tenant.subdomain or cfg.subdomain,
        "public_url": cfg.public_base_url if live else None,
        "company_name": tenant.company_name,
        "registry_url": _registry_base(),
        "tunnel_token_present": TUNNEL_TOKEN_PATH.is_file(),
        "local_url": f"http://127.0.0.1:{cfg.port}",
    }


@router.get("/health")
async def registry_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Local + optional central registry health check."""
    cfg = get_config()
    tenant = get_primary_tenant(db)
    local = {
        "ok": True,
        "service": "shogun-web",
        "subdomain": tenant.subdomain,
        "company_name": tenant.company_name,
        "time": datetime.now(timezone.utc).isoformat(),
    }

    base = _registry_base()
    central: Dict[str, Any] = {"configured": True, "url": f"{base}/api/health"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{base}/api/health")
            central.update(
                {
                    "ok": resp.status_code < 500,
                    "status_code": resp.status_code,
                }
            )
            try:
                central["body"] = resp.json()
            except Exception:
                central["body"] = resp.text[:300]
    except httpx.HTTPError as exc:
        central.update({"ok": False, "error": str(exc)})

    return {"local": local, "central": central}

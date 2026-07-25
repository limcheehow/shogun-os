"""Central registry client and local health/register routes."""

from __future__ import annotations

import logging
import platform
import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import require_admin
from config import get_config
from database import get_db, get_primary_tenant
from models import Department, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/registry", tags=["registry"])


class RegisterRequest(BaseModel):
    force: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


def build_registration_payload(db: Session) -> Dict[str, Any]:
    """Assemble tenant registration body for the central registry."""
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

    hostname = socket.gethostname()
    return {
        "subdomain": tenant.subdomain,
        "company_name": tenant.company_name,
        "timezone": tenant.timezone,
        "status": tenant.status,
        "public_base_url": cfg.public_base_url,
        "hostname": hostname,
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
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


async def register_with_central(
    db: Session,
    *,
    force: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """POST tenant identity to the configured central registry URL."""
    cfg = get_config()
    if not cfg.registry_url:
        return {
            "ok": False,
            "skipped": True,
            "reason": "registry_url not configured",
        }

    payload = build_registration_payload(db)
    if metadata:
        payload["metadata"] = metadata
    if force:
        payload["force"] = True

    url = cfg.registry_url.rstrip("/") + "/register"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if cfg.registry_api_key:
        headers["Authorization"] = f"Bearer {cfg.registry_api_key}"
        headers["X-API-Key"] = cfg.registry_api_key

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            body: Any
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:1000]}
            ok = resp.status_code < 400
            if not ok:
                logger.warning("Registry register failed %s: %s", resp.status_code, body)
            return {
                "ok": ok,
                "status_code": resp.status_code,
                "response": body,
                "registry_url": url,
                "payload": payload,
            }
    except httpx.HTTPError as exc:
        logger.warning("Registry unreachable: %s", exc)
        return {
            "ok": False,
            "error": str(exc),
            "registry_url": url,
            "payload": payload,
        }


@router.post("/register")
async def register_route(
    body: RegisterRequest,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Manually (re)register this tenant with the central registry."""
    result = await register_with_central(db, force=body.force, metadata=body.metadata)
    if result.get("skipped"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("reason") or "Registry not configured",
        )
    return result


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

    central: Dict[str, Any] = {"configured": bool(cfg.registry_url)}
    if cfg.registry_url:
        url = cfg.registry_url.rstrip("/") + "/health"
        headers = {}
        if cfg.registry_api_key:
            headers["Authorization"] = f"Bearer {cfg.registry_api_key}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                central.update(
                    {
                        "ok": resp.status_code < 500,
                        "status_code": resp.status_code,
                        "url": url,
                    }
                )
                try:
                    central["body"] = resp.json()
                except Exception:
                    central["body"] = resp.text[:300]
        except httpx.HTTPError as exc:
            central.update({"ok": False, "error": str(exc), "url": url})

    return {"local": local, "central": central}

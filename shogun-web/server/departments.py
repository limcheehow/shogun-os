"""Department detail, gbrain proxy, docs listing, and status endpoints."""

from __future__ import annotations

import logging
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user
from config import get_config
from database import get_db, get_primary_tenant
from models import Department, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/departments", tags=["departments"])


def _get_dept(db: Session, tenant_id: int, name: str) -> Department:
    dept = db.execute(
        select(Department).where(Department.tenant_id == tenant_id, Department.name == name)
    ).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return dept


def _redact_provider_config(cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(cfg or {})
    for key in list(out.keys()):
        if key.endswith(("_key", "_secret", "_token", "api_key", "password")) and out[key]:
            out[key] = "***"
    return out


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@router.get("/{name}")
async def get_department(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return department detail with redacted provider config."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    data = dept.to_dict()
    data["provider_config"] = _redact_provider_config(dept.provider_config)
    data["gateway_ws_url"] = (
        f"ws://localhost:{dept.gateway_port}/ws" if dept.gateway_port else None
    )
    return {"department": data}


@router.get("/{name}/brain")
async def get_department_brain(
    name: str,
    q: Optional[str] = Query(default=None, description="Optional search query"),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Proxy a lightweight listing/search against gbrain for this department source."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    source = name  # gbrain source id typically matches department folder name

    headers = {"Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if q:
                # Prefer hybrid search endpoint when available
                resp = await client.post(
                    f"{base}/api/search",
                    json={"query": q, "limit": limit, "source_id": source},
                    headers=headers,
                )
                if resp.status_code == 404:
                    resp = await client.get(
                        f"{base}/search",
                        params={"q": q, "limit": limit, "source": source},
                        headers=headers,
                    )
            else:
                resp = await client.get(
                    f"{base}/api/pages",
                    params={"limit": limit, "source_id": source},
                    headers=headers,
                )
                if resp.status_code == 404:
                    resp = await client.get(
                        f"{base}/pages",
                        params={"limit": limit, "source": source},
                        headers=headers,
                    )
    except httpx.HTTPError as exc:
        logger.warning("gbrain proxy error for %s: %s", name, exc)
        # Fall back to on-disk brain folder listing
        return {
            "ok": False,
            "error": f"gbrain unreachable: {exc}",
            "source": source,
            "pages": _list_brain_markdown(name, limit=limit),
            "fallback": "filesystem",
        }

    if resp.status_code >= 400:
        return {
            "ok": False,
            "error": resp.text[:500],
            "status_code": resp.status_code,
            "source": source,
            "pages": _list_brain_markdown(name, limit=limit),
            "fallback": "filesystem",
        }

    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text[:2000]}

    return {
        "ok": True,
        "source": source,
        "department": dept.name,
        "profile_name": dept.profile_name,
        "result": payload,
    }


def _list_brain_markdown(dept_name: str, *, limit: int = 50) -> List[Dict[str, Any]]:
    """List markdown pages under ~/brain/<dept> as a filesystem fallback."""
    cfg = get_config()
    root = Path(cfg.brain_root).expanduser() / dept_name
    if not root.is_dir():
        # also try profiles-style
        alt = Path(cfg.brain_root).expanduser() / f"{dept_name}"
        root = alt if alt.is_dir() else root
    pages: List[Dict[str, Any]] = []
    if not root.is_dir():
        return pages
    for path in sorted(root.rglob("*.md")):
        if path.name.startswith("."):
            continue
        rel = str(path.relative_to(root))
        pages.append(
            {
                "slug": rel.replace("\\", "/").rsplit(".", 1)[0],
                "path": str(path),
                "title": path.stem.replace("-", " ").replace("_", " ").title(),
            }
        )
        if len(pages) >= limit:
            break
    return pages


@router.get("/{name}/docs")
async def list_department_docs(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List department artifacts from the brain folder and Hermes profile directory."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    cfg = get_config()

    artifacts: List[Dict[str, Any]] = []

    # Brain markdown
    for page in _list_brain_markdown(name, limit=200):
        artifacts.append(
            {
                "type": "brain_page",
                "name": page["title"],
                "slug": page["slug"],
                "path": page["path"],
            }
        )

    # Hermes profile files
    profile_dirs = [
        Path.home() / ".hermes" / "profiles" / dept.profile_name,
        Path.home() / ".hermes" / dept.profile_name,
    ]
    interesting = {
        "SOUL.md",
        "AGENTS.md",
        "config.yaml",
        "scrum.yaml",
        "README.md",
    }
    for pdir in profile_dirs:
        if not pdir.is_dir():
            continue
        for path in sorted(pdir.rglob("*")):
            if not path.is_file():
                continue
            if path.name in interesting or path.suffix.lower() in {".md", ".yaml", ".yml", ".json"}:
                try:
                    rel = str(path.relative_to(pdir))
                except ValueError:
                    rel = path.name
                artifacts.append(
                    {
                        "type": "profile_file",
                        "name": path.name,
                        "path": str(path),
                        "relative": rel,
                        "profile": dept.profile_name,
                    }
                )

    # Shared skills that mention the department (lightweight)
    skills_root = Path.home() / ".hermes" / "skills"
    if skills_root.is_dir():
        for skill_md in skills_root.glob("*/SKILL.md"):
            artifacts.append(
                {
                    "type": "skill",
                    "name": skill_md.parent.name,
                    "path": str(skill_md),
                }
            )

    return {
        "department": dept.name,
        "profile_name": dept.profile_name,
        "count": len(artifacts),
        "artifacts": artifacts,
        "brain_root": str(Path(cfg.brain_root).expanduser() / name),
    }


@router.get("/{name}/status")
async def department_status(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Report gateway reachability and provider configuration status."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    cfg = get_config()

    gateway: Dict[str, Any] = {
        "port": dept.gateway_port,
        "listening": False,
        "health": None,
        "ws_url": f"ws://127.0.0.1:{dept.gateway_port}/ws" if dept.gateway_port else None,
    }
    if dept.gateway_port:
        gateway["listening"] = _port_open("127.0.0.1", int(dept.gateway_port))
        if gateway["listening"]:
            try:
                async with httpx.AsyncClient(timeout=2.5) as client:
                    resp = await client.get(f"http://127.0.0.1:{dept.gateway_port}/health")
                    gateway["health"] = {
                        "status_code": resp.status_code,
                        "body": resp.text[:300],
                    }
            except httpx.HTTPError as exc:
                gateway["health"] = {"error": str(exc)}

    provider_cfg = dept.provider_config or {}
    provider_status = {
        "configured": bool(provider_cfg.get("provider") or provider_cfg.get("api_key")),
        "provider": provider_cfg.get("provider"),
        "model": provider_cfg.get("model"),
        "has_api_key": bool(
            provider_cfg.get("api_key")
            or provider_cfg.get("openai_api_key")
            or provider_cfg.get("anthropic_api_key")
        ),
    }

    gbrain_ok = False
    gbrain_detail: Dict[str, Any] = {}
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(f"{cfg.gbrain_base_url.rstrip('/')}/health")
            gbrain_ok = resp.status_code < 500
            gbrain_detail = {"status_code": resp.status_code}
    except httpx.HTTPError as exc:
        gbrain_detail = {"error": str(exc)}

    profile_path = Path.home() / ".hermes" / "profiles" / dept.profile_name
    profile_exists = profile_path.is_dir()

    return {
        "department": dept.to_dict() | {"provider_config": _redact_provider_config(dept.provider_config)},
        "status": dept.status,
        "gateway": gateway,
        "provider": provider_status,
        "gbrain": {"ok": gbrain_ok, **gbrain_detail, "base_url": cfg.gbrain_base_url},
        "profile": {
            "name": dept.profile_name,
            "exists": profile_exists,
            "path": str(profile_path) if profile_exists else None,
        },
    }

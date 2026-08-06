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
        file_data = _list_brain_files(name, dept.profile_name, limit=limit)
        return {
            "ok": False,
            "error": f"gbrain unreachable: {exc}",
            "source": source,
            "pages": _list_brain_markdown(name, limit=limit),
            "files": file_data["files"],
            "folders": file_data["folders"],
            "fallback": "filesystem",
        }

    if resp.status_code >= 400:
        file_data = _list_brain_files(name, dept.profile_name, limit=limit)
        return {
            "ok": False,
            "error": resp.text[:500],
            "status_code": resp.status_code,
            "source": source,
            "pages": _list_brain_markdown(name, limit=limit),
            "files": file_data["files"],
            "folders": file_data["folders"],
            "fallback": "filesystem",
        }

    file_data = _list_brain_files(name, dept.profile_name, limit=limit)
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
        "files": file_data["files"],
        "folders": file_data["folders"],
    }


def _list_brain_files(dept_name: str, profile_name: str = "", *, limit: int = 500) -> Dict[str, Any]:
    """List all folders and files under ~/brain/<dept> and ~/.hermes/profiles/<profile_name>."""
    cfg = get_config()
    brain_root = Path(cfg.brain_root).expanduser() / dept_name
    if not brain_root.is_dir():
        alt = Path(cfg.brain_root).expanduser() / f"{dept_name}"
        brain_root = alt if alt.is_dir() else brain_root

    profile_root = Path.home() / ".hermes" / "profiles" / profile_name if profile_name else None

    files: List[Dict[str, Any]] = []
    folders_set = set()

    sources = [(brain_root, "brain")]
    if profile_root and profile_root.is_dir():
        sources.append((profile_root, "profile"))

    for root_dir, category in sources:
        if not root_dir.is_dir():
            continue
        for path in sorted(root_dir.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            rel = str(path.relative_to(root_dir)).replace("\\", "/")
            folder = str(Path(rel).parent).replace("\\", "/")
            if folder != ".":
                folders_set.add(f"{category}/{folder}" if category != "brain" else folder)

            files.append(
                {
                    "slug": rel.rsplit(".", 1)[0] if "." in rel else rel,
                    "rel_path": rel,
                    "folder": folder if folder != "." else "",
                    "category": category,
                    "name": path.name,
                    "full_path": str(path),
                    "ext": path.suffix.lower(),
                    "title": path.stem.replace("-", " ").replace("_", " ").title(),
                }
            )
            if len(files) >= limit:
                break

    return {
        "files": files,
        "folders": sorted(list(folders_set)),
    }


def _list_brain_markdown(dept_name: str, *, limit: int = 50) -> List[Dict[str, Any]]:
    """List markdown pages under ~/brain/<dept> as a filesystem fallback."""
    data = _list_brain_files(dept_name, limit=limit)
    return [f for f in data["files"] if f["ext"] == ".md"]


@router.get("/{name}/brain/file-content")
async def get_brain_file_content(
    name: str,
    path: str = Query(..., description="File path to read"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Read content of a file in department brain or profile directory."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    target = Path(path).expanduser()
    if not target.is_file():
        cfg = get_config()
        target = Path(cfg.brain_root).expanduser() / name / path
    if not target.is_file():
        target = Path.home() / ".hermes" / "profiles" / dept.profile_name / path
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {exc}")
    return {
        "name": target.name,
        "path": str(target),
        "ext": target.suffix.lower(),
        "content": content,
    }



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


def _get_chat_history_file(dept_name: str) -> Path:
    """Return path to persistent JSON chat history for a department."""
    cfg = get_config()
    history_dir = Path(cfg.db_path).parent / "chat_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / f"{dept_name.lower()}.json"


@router.get("/{name}/chat/history")
async def get_department_chat_history(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return saved chat history for a specific department."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    file_path = _get_chat_history_file(dept.name.lower())
    if not file_path.is_file():
        return []
    try:
        import json
        with file_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Error reading chat history for %s: %s", name, exc)
        return []


@router.post("/{name}/chat/messages")
async def save_department_chat_message(
    name: str,
    body: Dict[str, Any],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Persist chat messages for a specific department."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    file_path = _get_chat_history_file(dept.name.lower())

    incoming_messages = body.get("messages")
    if incoming_messages is None and "content" in body:
        incoming_messages = [body]
    if not isinstance(incoming_messages, list):
        raise HTTPException(status_code=400, detail="Invalid message payload")

    existing: List[Dict[str, Any]] = []
    if file_path.is_file():
        try:
            import json
            with file_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    existing = data
        except Exception:
            existing = []

    # Merge or append incoming messages
    existing_by_id = {m.get("id"): i for i, m in enumerate(existing) if m.get("id")}
    for msg in incoming_messages:
        msg_id = msg.get("id")
        if msg_id and msg_id in existing_by_id:
            existing[existing_by_id[msg_id]] = msg
        else:
            existing.append(msg)

    try:
        import json
        with file_path.open("w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2)
    except Exception as exc:
        logger.error("Failed to write chat history for %s: %s", name, exc)
        raise HTTPException(status_code=500, detail=f"Failed to save chat history: {exc}")

    return {"ok": True, "saved_count": len(existing)}


"""Onboarding wizard and department activation routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user, require_admin
from config import DEFAULT_DEPARTMENTS, get_config
from database import get_db, get_primary_tenant
from models import Department, OnboardingState, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["onboarding"])


class StepPayload(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)
    next_step: Optional[str] = None


class ConfigurePayload(BaseModel):
    provider: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class TestConnectionPayload(BaseModel):
    provider: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


def _get_onboarding(db: Session, tenant_id: int) -> OnboardingState:
    state = db.execute(
        select(OnboardingState).where(OnboardingState.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if state is None:
        state = OnboardingState(tenant_id=tenant_id, current_step="welcome", data={})
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _dept_catalog_meta(name: str) -> Dict[str, Any]:
    for spec in DEFAULT_DEPARTMENTS:
        if spec["name"] == name:
            return dict(spec)
    return {"name": name, "label": name, "profile_name": f"{name}-manager"}


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


@router.get("/onboarding/state")
async def get_onboarding_state(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return the tenant's onboarding wizard state."""
    tenant = get_primary_tenant(db)
    if user.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    state = _get_onboarding(db, tenant.id)
    return {
        "state": state.to_dict(),
        "user": user.to_dict(),
        "tenant": tenant.to_dict(),
    }


@router.post("/onboarding/step/{step}")
async def save_onboarding_step(
    step: str,
    body: StepPayload,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Persist data for a wizard step and advance ``current_step`` when asked."""
    tenant = get_primary_tenant(db)
    if user.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    state = _get_onboarding(db, tenant.id)
    if state.completed_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Onboarding already completed")

    merged = dict(state.data or {})
    step_bucket = dict(merged.get(step) or {})
    step_bucket.update(body.data or {})
    merged[step] = step_bucket
    state.data = merged
    state.current_step = body.next_step or step
    db.add(state)

    # Apply company profile fields when present
    company = step_bucket if step in {"company", "welcome", "profile"} else merged.get("company")
    if isinstance(company, dict):
        if company.get("company_name"):
            tenant.company_name = str(company["company_name"])
        if company.get("timezone"):
            tenant.timezone = str(company["timezone"])
        if company.get("logo_url") is not None:
            tenant.logo_url = str(company.get("logo_url") or "") or None
        db.add(tenant)

    db.commit()
    db.refresh(state)
    return {"ok": True, "state": state.to_dict(), "tenant": tenant.to_dict()}


@router.post("/onboarding/complete")
async def complete_onboarding(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Mark onboarding complete and clear first_login if password already changed."""
    tenant = get_primary_tenant(db)
    if user.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    state = _get_onboarding(db, tenant.id)
    state.completed_at = datetime.now(timezone.utc)
    state.current_step = "done"
    db.add(state)
    db.commit()
    db.refresh(state)
    return {"ok": True, "state": state.to_dict()}


# ---------------------------------------------------------------------------
# Departments (list / activate / configure / test) — also under /departments
# ---------------------------------------------------------------------------


@router.get("/departments")
async def list_departments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List all departments for the current tenant."""
    tenant = get_primary_tenant(db)
    depts = list(
        db.execute(select(Department).where(Department.tenant_id == tenant.id)).scalars()
    )
    items = []
    for d in depts:
        item = d.to_dict()
        meta = _dept_catalog_meta(d.name)
        item["label"] = meta.get("label", d.name)
        items.append(item)
    items.sort(key=lambda x: x["name"])
    return {"departments": items}


@router.post("/departments/{name}/activate")
async def activate_department(
    name: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Mark a department active (Hermes profile expected to be provisioned separately)."""
    tenant = get_primary_tenant(db)
    dept = db.execute(
        select(Department).where(Department.tenant_id == tenant.id, Department.name == name)
    ).scalar_one_or_none()
    if dept is None:
        # Auto-create unknown department from name
        cfg = get_config()
        meta = _dept_catalog_meta(name)
        offset = int(meta.get("port_offset") or (len(DEFAULT_DEPARTMENTS) + 1))
        dept = Department(
            tenant_id=tenant.id,
            name=name,
            profile_name=str(meta.get("profile_name") or f"{name}-manager"),
            status="inactive",
            provider_config={},
            gateway_port=cfg.gateway_port_base + offset,
        )
        db.add(dept)
        db.flush()

    dept.status = "active"
    if not dept.gateway_port:
        cfg = get_config()
        dept.gateway_port = cfg.gateway_port_base + abs(hash(name)) % 1000 + 1
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {"ok": True, "department": dept.to_dict()}


@router.post("/departments/{name}/configure")
async def configure_department(
    name: str,
    body: ConfigurePayload,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Save provider configuration JSON for a department."""
    tenant = get_primary_tenant(db)
    dept = db.execute(
        select(Department).where(Department.tenant_id == tenant.id, Department.name == name)
    ).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    current = dict(dept.provider_config or {})
    if body.provider:
        current["provider"] = body.provider
    current.update(body.config or {})
    # Never store blank secrets over existing ones when key present but empty
    for key in list(current.keys()):
        if key.endswith(("_key", "_secret", "_token", "api_key", "password")):
            if current[key] in ("", None) and (dept.provider_config or {}).get(key):
                current[key] = (dept.provider_config or {})[key]
    dept.provider_config = current
    db.add(dept)
    db.commit()
    db.refresh(dept)

    # Redact secrets in response
    safe = dept.to_dict()
    cfg_out = dict(safe.get("provider_config") or {})
    for key in list(cfg_out.keys()):
        if key.endswith(("_key", "_secret", "_token", "api_key", "password")) and cfg_out[key]:
            cfg_out[key] = "***"
    safe["provider_config"] = cfg_out
    return {"ok": True, "department": safe}


async def _test_openai_compatible(base_url: str, api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = base_url.rstrip("/") + "/models"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": resp.text[:500],
            }
        data = resp.json()
        models = []
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            models = [m.get("id") for m in data["data"] if isinstance(m, dict)]
        result: Dict[str, Any] = {"ok": True, "status_code": resp.status_code, "models": models[:20]}
        if model and models and model not in models:
            result["warning"] = f"Model '{model}' not listed by provider"
        return result


async def _test_openrouter(api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
    return await _test_openai_compatible(
        "https://openrouter.ai/api/v1", api_key, model=model
    )


async def _test_anthropic(api_key: str) -> Dict[str, Any]:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get("https://api.anthropic.com/v1/models", headers=headers)
        if resp.status_code >= 400:
            # Some keys can call messages but not list models — treat 401/403 as fail
            return {"ok": False, "status_code": resp.status_code, "error": resp.text[:500]}
        return {"ok": True, "status_code": resp.status_code}


async def _test_gateway_port(port: Optional[int]) -> Dict[str, Any]:
    if not port:
        return {"ok": False, "error": "No gateway_port configured"}
    url = f"http://127.0.0.1:{port}/health"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            return {
                "ok": resp.status_code < 500,
                "status_code": resp.status_code,
                "url": url,
            }
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "url": url}


@router.post("/departments/{name}/test-connection")
async def test_department_connection(
    name: str,
    body: TestConnectionPayload,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Probe the configured LLM provider and optional local Hermes gateway."""
    tenant = get_primary_tenant(db)
    dept = db.execute(
        select(Department).where(Department.tenant_id == tenant.id, Department.name == name)
    ).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    stored = dict(dept.provider_config or {})
    cfg = {**stored, **(body.config or {})}
    provider = (body.provider or cfg.get("provider") or "openrouter").lower()
    api_key = str(cfg.get("api_key") or cfg.get("openai_api_key") or "")
    model = cfg.get("model")
    base_url = str(cfg.get("base_url") or "")

    provider_result: Dict[str, Any]
    try:
        if provider in {"openrouter"}:
            if not api_key:
                provider_result = {"ok": False, "error": "api_key required"}
            else:
                provider_result = await _test_openrouter(api_key, model=model)
        elif provider in {"openai", "openai-compatible", "custom"}:
            if not base_url:
                base_url = "https://api.openai.com/v1"
            if not api_key and provider != "custom":
                provider_result = {"ok": False, "error": "api_key required"}
            else:
                provider_result = await _test_openai_compatible(base_url, api_key, model=model)
        elif provider in {"anthropic", "claude"}:
            if not api_key:
                provider_result = {"ok": False, "error": "api_key required"}
            else:
                provider_result = await _test_anthropic(api_key)
        elif provider in {"local", "ollama"}:
            base_url = base_url or "http://127.0.0.1:11434/v1"
            provider_result = await _test_openai_compatible(base_url, api_key or "ollama", model=model)
        else:
            provider_result = {
                "ok": False,
                "error": f"Unsupported provider '{provider}'",
            }
    except Exception as exc:
        logger.exception("Provider test failed for %s", name)
        provider_result = {"ok": False, "error": str(exc)}

    gateway_result = await _test_gateway_port(dept.gateway_port)

    return {
        "ok": bool(provider_result.get("ok")),
        "provider": provider,
        "provider_result": provider_result,
        "gateway_result": gateway_result,
        "department": name,
    }


@router.post("/departments/{name}/deactivate")
async def deactivate_department(
    name: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Set department status to inactive."""
    tenant = get_primary_tenant(db)
    dept = db.execute(
        select(Department).where(Department.tenant_id == tenant.id, Department.name == name)
    ).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    dept.status = "inactive"
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {"ok": True, "department": dept.to_dict()}

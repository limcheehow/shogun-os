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

    file_data = _list_brain_files(name, dept.profile_name, limit=limit, q=q)
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


def _ensure_default_brain_docs(dept_name: str) -> None:
    """Ensure default brain markdown files exist for a department if ~/brain/<dept> is empty or missing."""
    try:
        cfg = get_config()
        brain_root = Path(cfg.brain_root).expanduser() / dept_name.lower()
        if brain_root.is_dir() and any(brain_root.glob("**/*.md")):
            return  # Already has documents

        brain_root.mkdir(parents=True, exist_ok=True)
        key = dept_name.lower()

        if key == "crm":
            (brain_root / "key-accounts").mkdir(parents=True, exist_ok=True)
            (brain_root / "pipeline").mkdir(parents=True, exist_ok=True)
            (brain_root / "playbooks").mkdir(parents=True, exist_ok=True)

            (brain_root / "key-accounts" / "parkson-enterprise-agreement.md").write_text(
                "# Parkson Departmental Stores — Enterprise Account Overview\n\n"
                "## Executive Summary\nParkson Corporation is Shogun Retail Enterprise's largest wholesale customer in Malaysia, contributing **RM 1.45M YTD** in gross orders across 11 nationwide departmental store outlets.\n\n"
                "## Account Metadata\n- **Account Status**: Active Premier Partner\n- **Credit Terms**: 60 Days Net (RM 500,000 credit limit)\n- **Primary Owner**: Chee How (VP of Sales)\n- **Annual Contract Value (ACV)**: RM 2,800,000\n\n"
                "## Core Product Categories\n1. **Apparel & Fashion**: Premium corporate uniforms & designer outerwear.\n2. **Lifestyle & Home**: Household merchandise & eco-friendly kitchenware.\n\n"
                "## Account Contacts\n| Role | Contact Name | Email | Direct Line |\n|---|---|---|---|\n| Procurement Director | Tan Sri Kenneth | k.tan@parkson.com.my | +60 3-2143 8890 |\n| Category Buyer | Amanda Seong | a.seong@parkson.com.my | +60 3-2143 8892 |\n| Logistics Coordinator | Raymond Lim | r.lim@parkson.com.my | +60 3-2143 8895 |\n\n"
                "## Quarterly Performance & Revenue Target\n- **Q1 Delivered**: RM 650,000 (102% of target)\n- **Q2 Delivered**: RM 800,000 (105% of target)\n- **Q3 Forecast**: RM 750,000 (Pipeline Win Probability: **78%**)\n",
                encoding="utf-8"
            )

            (brain_root / "key-accounts" / "aeon-outlets-contract.md").write_text(
                "# Aeon Retail Outlets — Master Supply Contract\n\n"
                "## Account Overview\nAeon Retail Malaysia operates 28 hypermarkets and superstores. Shogun Retail Enterprise supplies consumer electronics and home accessories under a wholesale consignment model.\n\n"
                "## Key Deal Terms\n- **Contract Duration**: 24 Months (Expiring Dec 2027)\n- **Primary Owner**: Nazrul (Senior Account Manager)\n- **YTD Sales Revenue**: RM 1,180,000.00\n- **Consignment Discount Rate**: 18.5%\n\n"
                "## Top Selling SKUs at Aeon\n1. *Shogun Smart Home Hub v2* (SKU-ELE-001)\n2. *Ergonomic Lumbar Office Cushion* (SKU-LIF-004)\n3. *Wireless Noise-Canceling Headset* (SKU-ELE-008)\n\n"
                "## Recent Activity Notes\n- **2026-07-28**: Negotiated 15% increase in floor display space for Mid-Valley MegaMall outlet.\n- **2026-08-02**: Resolved minor delivery delay for Tebrau City JB store.\n",
                encoding="utf-8"
            )

            (brain_root / "pipeline" / "q3-wholesale-pipeline-review.md").write_text(
                "# Q3 B2B Wholesale Pipeline Forecast & Strategy\n\n"
                "## Executive Summary\nTotal active B2B wholesale pipeline stands at **RM 8,500,000.00** across 38 qualified opportunities. Weighted pipeline value is estimated at **RM 3,850,000.00** with an overall win-rate of **74%**.\n\n"
                "## Pipeline Stage Breakdown\n| Stage | Deal Count | Total Value (MYR) | Weighted Value |\n|---|---|---|---|\n| Lead | 10 | RM 1,500,000 | RM 300,000 |\n| Prospecting | 8 | RM 2,100,000 | RM 630,000 |\n| Qualified | 7 | RM 1,850,000 | RM 925,000 |\n| Quote Issued | 6 | RM 1,650,000 | RM 1,155,000 |\n| Tender Finalist | 3 | RM 900,000 | RM 720,000 |\n| Confirmed | 4 | RM 500,000 | RM 500,000 |\n\n"
                "## Strategic Action Items\n1. **Accelerate Lotus Supermarkets Tender**: Complete product testing by Aug 15.\n2. **Expand SOGO Fashion Range**: Offer 5% early-payment rebate on Q4 pre-orders.\n",
                encoding="utf-8"
            )

            (brain_root / "playbooks" / "lead-qualification-sop.md").write_text(
                "# Standard Operating Procedure: B2B Lead Qualification\n\n"
                "## BANT Qualification Framework\nEvery incoming sales lead must be qualified against the BANT framework before assignment:\n- **Budget**: Minimum annual retail purchasing budget of RM 100,000.\n- **Authority**: Primary decision maker must be Category Manager, Procurement Head, or C-Level.\n- **Need**: Urgent demand for retail apparel, electronics, or corporate gift merchandise.\n- **Timeline**: Decision horizon within 90 days.\n\n"
                "## Response SLA\n- **Inbound Contact Form**: Contact within **15 minutes**.\n- **WhatsApp Inquiry**: Contact within **5 minutes**.\n",
                encoding="utf-8"
            )

        elif key == "procurement":
            (brain_root / "suppliers").mkdir(parents=True, exist_ok=True)
            (brain_root / "purchase-orders").mkdir(parents=True, exist_ok=True)
            (brain_root / "inventory").mkdir(parents=True, exist_ok=True)

            (brain_root / "suppliers" / "textile-apparel-vendor-contract.md").write_text(
                "# Master Supplier Agreement — Master Textile Ltd\n\n"
                "## Supplier Profile\n- **Vendor Name**: Master Textile & Apparel Manufacturing Ltd\n- **Location**: Penang Free Industrial Zone, Malaysia\n- **Vendor ID**: VEN-APP-001\n- **Payment Terms**: 45 Days Net via Bank Transfer\n\n"
                "## Contract Details\n- **Scope**: Exclusive supply of organic cotton apparel and corporate uniform merchandise.\n- **Quality Assurance Target**: Defect rate strictly **< 0.5%** per production batch.\n- **Lead Time Guarantee**: 14 Days from Purchase Order receipt.\n\n"
                "## Key Contacts\n| Role | Contact Name | Email | Phone |\n|---|---|---|---|\n| Account Director | Mr. Robert Chen | r.chen@mastertextile.com | +60 4-643 1188 |\n| QA Manager | Sarah Hisham | s.hisham@mastertextile.com | +60 4-643 1192 |\n",
                encoding="utf-8"
            )

            (brain_root / "suppliers" / "electronics-oem-supplier-agreement.md").write_text(
                "# Consumer Electronics OEM Master Supply Agreement\n\n"
                "## Vendor Overview\n- **Vendor Name**: Apex Tech OEM Corporation\n- **Category**: Consumer Electronics & Smart Home Devices\n- **Vendor ID**: VEN-ELE-004\n- **Currency**: USD / MYR Fixed Exchange Rate Contract\n\n"
                "## SLA & Delivery Metrics\n- **Minimum Order Quantity (MOQ)**: 500 Units per order\n- **Warranty Support**: 24-Month full replacement warranty for defective units\n- **On-Time Delivery SLA**: 98.5% compliance\n\n"
                "## Pending Accounts Payable\n- **Current Unpaid Invoices**: RM 210,000.00 (Invoice #INV-2026-088 due Aug 25)\n",
                encoding="utf-8"
            )

            (brain_root / "purchase-orders" / "po-approval-matrix-2026.md").write_text(
                "# 2026 Procurement & Purchase Requisition Approval Matrix\n\n"
                "## Authority Financial Thresholds\nAll purchase requisitions (PR) and purchase orders (PO) must follow the corporate sign-off matrix below:\n\n"
                "| Requisition Amount (MYR) | Required Approvers | SLA Turnaround |\n|---|---|---|\n| Below RM 5,000 | Department Manager | 2 Hours |\n| RM 5,001 – RM 25,000 | Procurement Head | 6 Hours |\n| RM 25,001 – RM 100,000 | CFO + Procurement Head | 12 Hours |\n| Above RM 100,000 | CEO + CFO Board Sign-Off | 24 Hours |\n\n"
                "## Emergency Purchase Orders\nFor urgent stockouts affecting retail outlets, emergency POs up to RM 20,000 can be pre-approved via Slack slash command `/procure emergency`.\n",
                encoding="utf-8"
            )

            (brain_root / "inventory" / "safety-stock-policy-retail-stores.md").write_text(
                "# Retail Safety Stock & Reorder Buffer SOP\n\n"
                "## Objective\nTo prevent retail store stockouts while keeping total inventory holding costs optimized under RM 1.2M.\n\n"
                "## Category Buffer Levels\n- **Fast Moving Apparel**: 14 Days Safety Stock\n- **Consumer Electronics**: 10 Days Safety Stock\n- **Lifestyle & Home**: 21 Days Safety Stock\n",
                encoding="utf-8"
            )

        elif key == "finance":
            (brain_root / "reports").mkdir(parents=True, exist_ok=True)
            (brain_root / "reports" / "financial-statement-q2-2026.md").write_text(
                "# Q2 2026 Financial P&L Statement & Treasury Summary\n\n"
                "## Executive Revenue Summary\n- **Gross Sales YTD**: **RM 4,850,000.00**\n- **Net Operating Income**: RM 1,280,000.00\n- **Net Margin**: **26.4%**\n- **Cash Runway**: **18.4 Months**\n\n"
                "## Receivables & Payables\n- **Accounts Receivable (AR)**: RM 485,000.00 (10% credit terms with Parkson & Aeon)\n- **Accounts Payable (AP)**: RM 210,000.00 (Supplier invoices due within 30 days)\n",
                encoding="utf-8"
            )
    except Exception as exc:
        logger.warning("Could not auto-seed brain docs for %s: %s", dept_name, exc)


def _list_brain_files(dept_name: str, profile_name: str = "", *, limit: int = 500, q: Optional[str] = None) -> Dict[str, Any]:
    """List all folders and files under ~/brain/<dept> and ~/.hermes/profiles/<profile_name>, searching file content if q is provided."""
    _ensure_default_brain_docs(dept_name)
    cfg = get_config()
    brain_root = Path(cfg.brain_root).expanduser() / dept_name
    if not brain_root.is_dir():
        alt = Path(cfg.brain_root).expanduser() / f"{dept_name}"
        brain_root = alt if alt.is_dir() else brain_root

    profile_root = Path.home() / ".hermes" / "profiles" / profile_name if profile_name else None

    files: List[Dict[str, Any]] = []
    folders_set = set()

    query_str = q.strip().lower() if q and q.strip() else None

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

            snippet = None
            if query_str:
                name_match = query_str in path.name.lower() or query_str in rel.lower()
                content_match = False
                if path.suffix.lower() in [".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".py", ".js", ".ts", ".html"]:
                    try:
                        content_txt = path.read_text(encoding="utf-8", errors="ignore")
                        idx = content_txt.lower().find(query_str)
                        if idx >= 0:
                            content_match = True
                            start_i = max(0, idx - 40)
                            end_i = min(len(content_txt), idx + 100)
                            snippet = "..." + content_txt[start_i:end_i].replace("\n", " ") + "..."
                    except Exception:
                        pass
                if not (name_match or content_match):
                    continue

            if folder != ".":
                folders_set.add(f"{category}/{folder}" if category != "brain" else folder)

            item = {
                "slug": rel.rsplit(".", 1)[0] if "." in rel else rel,
                "rel_path": rel,
                "folder": folder if folder != "." else "",
                "category": category,
                "name": path.name,
                "full_path": str(path),
                "ext": path.suffix.lower(),
                "title": path.stem.replace("-", " ").replace("_", " ").title(),
            }
            if snippet:
                item["snippet"] = snippet

            files.append(item)
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


@router.delete("/chat/history/all")
async def clear_all_chat_history() -> Dict[str, Any]:
    """Delete all persistent department chat history files."""
    cfg = get_config()
    history_dir = Path(cfg.db_path).parent / "chat_history"
    deleted_count = 0
    if history_dir.is_dir():
        for f in history_dir.glob("*.json"):
            try:
                f.unlink()
                deleted_count += 1
            except Exception as exc:
                logger.warning("Could not delete chat history file %s: %s", f, exc)
    return {"ok": True, "deleted_count": deleted_count}


@router.delete("/{name}/chat/history")
async def clear_department_chat_history(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Delete saved chat history for a specific department."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    file_path = _get_chat_history_file(dept.name.lower())
    if file_path.is_file():
        try:
            file_path.unlink()
        except Exception as exc:
            logger.warning("Could not delete file %s: %s", file_path, exc)
    return {"ok": True, "department": dept.name.lower()}


import shutil
import uuid
from fastapi import File, UploadFile, Body

_DEPARTMENT_CONNECTORS: Dict[str, List[Dict[str, Any]]] = {
    "finance": [
        {
            "id": "bukku",
            "name": "Bukku Accounting",
            "category": "Accounting & Tax",
            "description": "Cloud accounting software for Malaysian SMEs with automated e-invoicing.",
            "logo_icon": "BookOpen",
            "status": "connected",
            "connected_at": "2026-08-01T10:00:00Z",
            "config_summary": "Connected to Bukku Org #BK-88412"
        },
        {
            "id": "qbo",
            "name": "QuickBooks Online",
            "category": "Accounting",
            "description": "Sync chart of accounts, bills, and customer invoices.",
            "logo_icon": "DollarSign",
            "status": "disconnected"
        },
        {
            "id": "xero",
            "name": "Xero",
            "category": "Accounting & AR",
            "description": "Automated bank reconciliation feeds and invoice syncing.",
            "logo_icon": "FileText",
            "status": "disconnected"
        },
        {
            "id": "stripe",
            "name": "Stripe Payments",
            "category": "Payment Gateway",
            "description": "Real-time payment capture and payout reconciliation.",
            "logo_icon": "CreditCard",
            "status": "connected",
            "connected_at": "2026-08-03T14:30:00Z",
            "config_summary": "Stripe Live Account acct_1N9x..."
        },
        {
            "id": "sql_account",
            "name": "SQL Account",
            "category": "ERP & Tax",
            "description": "Malaysian GST/SST compliant desktop & cloud bridge.",
            "logo_icon": "Database",
            "status": "disconnected"
        }
    ],
    "hr": [
        {
            "id": "bamboohr",
            "name": "BambooHR",
            "category": "HRIS & People",
            "description": "Employee database, onboarding workflows, and time-off tracking.",
            "logo_icon": "BookOpen",
            "status": "connected",
            "config_summary": "Synced 42 active employee records"
        },
        {
            "id": "payroll_my",
            "name": "Kakitangan Payroll",
            "category": "Payroll & EPF",
            "description": "Malaysian EPF, SOCSO, EIS, and PCB tax calculation bridge.",
            "logo_icon": "DollarSign",
            "status": "connected",
            "config_summary": "PCB / EPF auto-filing enabled"
        }
    ],
    "crm": [
        {
            "id": "hubspot",
            "name": "HubSpot CRM",
            "category": "Sales & Deals",
            "description": "Two-way pipeline sync, contact tracking, and deal stage analytics.",
            "logo_icon": "Handshake",
            "status": "connected",
            "config_summary": "HubSpot Portal #894102"
        },
        {
            "id": "salesforce",
            "name": "Salesforce Sales Cloud",
            "category": "Enterprise CRM",
            "description": "Account management and enterprise deal stage tracking.",
            "logo_icon": "Database",
            "status": "disconnected"
        }
    ],
    "procurement": [
        {
            "id": "sap_ariba",
            "name": "SAP Ariba",
            "category": "Supplier Portal",
            "description": "Purchase order requisitions and vendor contract lifecycles.",
            "logo_icon": "Package",
            "status": "connected",
            "config_summary": "Connected to SAP Ariba Network"
        }
    ],
    "engineering": [
        {
            "id": "github",
            "name": "GitHub Enterprise",
            "category": "Source Control & CI/CD",
            "description": "Repository sync, PR code review triggers, and CI workflow status.",
            "logo_icon": "Database",
            "status": "connected",
            "config_summary": "GitHub Org @limcheehow"
        }
    ]
}

_DEPARTMENT_SKILLS: Dict[str, List[Dict[str, Any]]] = {
    "finance": [
        {
            "id": "ar-dunning",
            "name": "AR Overdue Dunning Bot",
            "description": "Automatically generates & sends polite WhatsApp/email reminders for overdue receivables.",
            "category": "Finance",
            "installed": True,
            "version": "v1.4.0",
            "author": "Shogun OS Core"
        },
        {
            "id": "bank-reconciliation",
            "name": "Bank Statement Auto-Matcher",
            "description": "Matches bank feed deposits against unpaid customer invoices automatically.",
            "category": "Finance",
            "installed": True,
            "version": "v2.1.0",
            "author": "Shogun OS Core"
        }
    ],
    "crm": [
        {
            "id": "pipeline-scoring",
            "name": "CRM Deal Win-Probability Scorer",
            "description": "Predicts deal win rates based on buyer engagement and stage velocity.",
            "category": "CRM/Sales",
            "installed": True,
            "version": "v2.0.0",
            "author": "Sales Intelligence"
        },
        {
            "id": "lead-enricher",
            "name": "B2B Lead Enrichment & Contact Finder",
            "description": "Enriches raw leads with company size, verified executive email addresses, and LinkedIn profiles.",
            "category": "CRM/Sales",
            "installed": True,
            "version": "v1.3.0",
            "author": "Growth Pack"
        }
    ],
    "hr": [
        {
            "id": "leave-approver",
            "name": "Leave Request Auto-Approver",
            "description": "Validates team leave balances and checks calendar coverage before auto-approving PTO.",
            "category": "HR",
            "installed": True,
            "version": "v1.1.0",
            "author": "Shogun HR Pack"
        },
        {
            "id": "leave-policy-bot",
            "name": "HR Leave Policy & FAQ Assistant",
            "description": "Answers employee queries regarding annual leave, MC submission, and maternity policy.",
            "category": "HR",
            "installed": True,
            "version": "v1.0.0",
            "author": "Shogun HR Pack"
        }
    ],
    "procurement": [
        {
            "id": "po-approval-flow",
            "name": "Procurement Threshold Approval Router",
            "description": "Routes purchase requisitions over RM 50k to executive managers for authorization.",
            "category": "Procurement",
            "installed": True,
            "version": "v1.2.0",
            "author": "Ops Pack"
        },
        {
            "id": "vendor-scorecard",
            "name": "Supplier Performance & SLA Evaluator",
            "description": "Tracks vendor delivery lead times, order defect rates, and benchmark pricing variance.",
            "category": "Procurement",
            "installed": True,
            "version": "v1.5.0",
            "author": "Vendor Intelligence"
        }
    ],
    "coding": [
        {
            "id": "code-reviewer",
            "name": "Automated Pull Request Code Reviewer",
            "description": "Scans pull requests for security vulnerabilities, syntax issues, and missing tests.",
            "category": "Coding",
            "installed": True,
            "version": "v3.1.0",
            "author": "DevOps Suite"
        },
        {
            "id": "unit-test-gen",
            "name": "Automated Unit Test Suite Generator",
            "description": "Parses typescript/python code and generates high-coverage unit tests with mocks.",
            "category": "Coding",
            "installed": True,
            "version": "v2.0.1",
            "author": "QA Automation"
        }
    ],
    "operations": [
        {
            "id": "inventory-reorder",
            "name": "Retail Safety Stock & Auto-Reorder Trigger",
            "description": "Monitors retail SKU stock levels and generates automated purchase orders for low items.",
            "category": "Operations",
            "installed": True,
            "version": "v1.8.0",
            "author": "Supply Chain Pack"
        },
        {
            "id": "sla-monitor",
            "name": "Logistics Delivery & SLA Threshold Tracker",
            "description": "Tracks courier shipments in real-time and alerts store managers on delayed deliveries.",
            "category": "Operations",
            "installed": True,
            "version": "v1.1.4",
            "author": "Logistics Intelligence"
        }
    ],
    "executive": [
        {
            "id": "csuite-briefing",
            "name": "Daily C-Suite Executive KPI Briefing",
            "description": "Summarizes net margin, cash runway, pending AP/AR, and revenue variance into daily briefings.",
            "category": "Executive",
            "installed": True,
            "version": "v2.5.0",
            "author": "Executive Suite"
        }
    ]
}

_ALL_SKILLS: List[Dict[str, Any]] = [
    # Finance (3 skills)
    {
        "id": "ar-dunning",
        "name": "AR Overdue Dunning Bot",
        "description": "Automatically generates & sends polite WhatsApp/email reminders for overdue receivables.",
        "category": "Finance",
        "installed": True,
        "version": "v1.4.0",
        "department_keys": ["finance"]
    },
    {
        "id": "bank-reconciliation",
        "name": "Bank Statement Auto-Matcher",
        "description": "Matches bank feed deposits against unpaid customer invoices automatically.",
        "category": "Finance",
        "installed": True,
        "version": "v2.1.0",
        "department_keys": ["finance"]
    },
    {
        "id": "invoice-ocr",
        "name": "Supplier Invoice OCR Reader",
        "description": "Extracts line items, tax numbers, and totals from PDF vendor invoices into AP bills.",
        "category": "Finance",
        "installed": False,
        "version": "v1.1.0",
        "department_keys": ["finance", "procurement"]
    },
    # CRM/Sales (3 skills)
    {
        "id": "pipeline-scoring",
        "name": "CRM Deal Win-Probability Scorer",
        "description": "Predicts deal win rates based on buyer engagement and stage velocity.",
        "category": "CRM/Sales",
        "installed": True,
        "version": "v2.0.0",
        "department_keys": ["crm"]
    },
    {
        "id": "lead-enricher",
        "name": "B2B Lead Enrichment & Contact Finder",
        "description": "Enriches raw leads with company size, verified executive email addresses, and LinkedIn profiles.",
        "category": "CRM/Sales",
        "installed": True,
        "version": "v1.3.0",
        "department_keys": ["crm"]
    },
    {
        "id": "churn-predictor",
        "name": "Customer Retention & Churn Risk Predictor",
        "description": "Analyzes wholesale re-order intervals and flags accounts at high risk of churning.",
        "category": "CRM/Sales",
        "installed": False,
        "version": "v1.0.5",
        "department_keys": ["crm"]
    },
    # HR (3 skills)
    {
        "id": "leave-approver",
        "name": "Leave Request Auto-Approver",
        "description": "Validates team leave balances and checks calendar coverage before auto-approving PTO.",
        "category": "HR",
        "installed": True,
        "version": "v1.1.0",
        "department_keys": ["hr"]
    },
    {
        "id": "leave-policy-bot",
        "name": "HR Leave Policy & FAQ Assistant",
        "description": "Answers employee queries regarding annual leave, MC submission, and maternity policy.",
        "category": "HR",
        "installed": True,
        "version": "v1.0.0",
        "department_keys": ["hr"]
    },
    {
        "id": "resume-screener",
        "name": "AI Resume & Candidate Matching Screener",
        "description": "Parses incoming job applicant CVs and scores them against department role requirements.",
        "category": "HR",
        "installed": False,
        "version": "v1.2.0",
        "department_keys": ["hr"]
    },
    # Procurement (3 skills)
    {
        "id": "po-approval-flow",
        "name": "Procurement Threshold Approval Router",
        "description": "Routes purchase requisitions over RM 50k to executive managers for authorization.",
        "category": "Procurement",
        "installed": True,
        "version": "v1.2.0",
        "department_keys": ["procurement"]
    },
    {
        "id": "vendor-scorecard",
        "name": "Supplier Performance & SLA Evaluator",
        "description": "Tracks vendor delivery lead times, order defect rates, and benchmark pricing variance.",
        "category": "Procurement",
        "installed": True,
        "version": "v1.5.0",
        "department_keys": ["procurement"]
    },
    {
        "id": "rfq-generator",
        "name": "Automated RFQ & Bid Comparison Tool",
        "description": "Generates Request for Quotations and compares multiple supplier bids side-by-side.",
        "category": "Procurement",
        "installed": False,
        "version": "v1.0.1",
        "department_keys": ["procurement"]
    },
    # Coding (3 skills)
    {
        "id": "code-reviewer",
        "name": "Automated Pull Request Code Reviewer",
        "description": "Scans pull requests for security vulnerabilities, syntax issues, and missing tests.",
        "category": "Coding",
        "installed": True,
        "version": "v3.1.0",
        "department_keys": ["coding"]
    },
    {
        "id": "unit-test-gen",
        "name": "Automated Unit Test Suite Generator",
        "description": "Parses typescript/python code and generates high-coverage unit tests with mocks.",
        "category": "Coding",
        "installed": True,
        "version": "v2.0.1",
        "department_keys": ["coding"]
    },
    {
        "id": "docker-optimizer",
        "name": "Dockerfile & CI/CD Security Hardener",
        "description": "Audits container images for vulnerable OS dependencies and optimizes build cache layers.",
        "category": "Coding",
        "installed": False,
        "version": "v1.4.0",
        "department_keys": ["coding"]
    },
    # Operations (3 skills)
    {
        "id": "inventory-reorder",
        "name": "Retail Safety Stock & Auto-Reorder Trigger",
        "description": "Monitors retail SKU stock levels and generates automated purchase orders for low items.",
        "category": "Operations",
        "installed": True,
        "version": "v1.8.0",
        "department_keys": ["operations"]
    },
    {
        "id": "sla-monitor",
        "name": "Logistics Delivery & SLA Threshold Tracker",
        "description": "Tracks courier shipments in real-time and alerts store managers on delayed deliveries.",
        "category": "Operations",
        "installed": True,
        "version": "v1.1.4",
        "department_keys": ["operations"]
    },
    {
        "id": "shift-scheduler",
        "name": "Retail Store Shift & Roster Planner",
        "description": "Schedules retail store staff shifts considering foot-traffic forecasts and labor laws.",
        "category": "Operations",
        "installed": False,
        "version": "v1.0.0",
        "department_keys": ["operations"]
    },
    # Executive (3 skills)
    {
        "id": "csuite-briefing",
        "name": "Daily C-Suite Executive KPI Briefing",
        "description": "Summarizes net margin, cash runway, pending AP/AR, and revenue variance into daily briefings.",
        "category": "Executive",
        "installed": True,
        "version": "v2.5.0",
        "department_keys": ["executive"]
    },
    {
        "id": "board-deck-gen",
        "name": "Financial P&L Board Report Slide Generator",
        "description": "Compiles P&L statement, revenue breakdown, and budget variances into executive slide decks.",
        "category": "Executive",
        "installed": False,
        "version": "v1.1.0",
        "department_keys": ["executive"]
    },
    {
        "id": "competitor-radar",
        "name": "Retail Industry Competitor Pricing Radar",
        "description": "Monitors competitor promotions, pricing shifts, and retail market intelligence.",
        "category": "Executive",
        "installed": False,
        "version": "v1.0.2",
        "department_keys": ["executive"]
    }
]


@router.post("/{name}/chat/upload")
async def upload_chat_file(
    name: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Store uploaded image or document file for department chat."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    cfg = get_config()
    upload_dir = Path(cfg.db_path).parent / "chat_uploads" / dept.name.lower()
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "file").suffix.lower()
    file_id = f"up-{uuid.uuid4().hex[:10]}"
    safe_name = f"{file_id}_{Path(file.filename or 'file').name}"
    target_path = upload_dir / safe_name

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = target_path.stat().st_size
    mime = file.content_type or "application/octet-stream"
    is_image = mime.startswith("image/") or ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]

    rel_url = f"/api/chat/uploads/{dept.name.lower()}/{safe_name}"

    return {
        "ok": True,
        "attachment": {
            "id": file_id,
            "name": file.filename or safe_name,
            "url": rel_url,
            "mime_type": mime,
            "size_bytes": size,
            "is_image": is_image,
        }
    }


@router.get("/{name}/connectors")
async def list_department_connectors(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return software connectors for a department (Finance supported first)."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    key = dept.name.lower()
    connectors = _DEPARTMENT_CONNECTORS.get(key, [])
    return {"connectors": connectors}


@router.post("/{name}/connectors/{connector_id}/toggle")
async def toggle_department_connector(
    name: str,
    connector_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Toggle connection status for a department connector."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    key = dept.name.lower()
    items = _DEPARTMENT_CONNECTORS.get(key, [])
    for conn in items:
        if conn["id"] == connector_id:
            if conn["status"] == "connected":
                conn["status"] = "disconnected"
                conn.pop("connected_at", None)
            else:
                conn["status"] = "connected"
                conn["connected_at"] = "2026-08-06T14:00:00Z"
                conn["config_summary"] = f"Connected to {conn['name']}"
            return {"ok": True, "connector": conn}
    raise HTTPException(status_code=404, detail="Connector not found")


@router.get("/{name}/skills")
async def list_department_skills(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return downloaded/installed skills for a department."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    key = dept.name.lower()
    skills = _DEPARTMENT_SKILLS.get(key, [])
    return {"skills": skills}


@router.delete("/{name}/skills/{skill_id}")
async def delete_department_skill(
    name: str,
    skill_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Remove/uninstall a skill from a department."""
    tenant = get_primary_tenant(db)
    dept = _get_dept(db, tenant.id, name)
    key = dept.name.lower()
    items = _DEPARTMENT_SKILLS.get(key, [])
    _DEPARTMENT_SKILLS[key] = [s for s in items if s["id"] != skill_id]
    return {"ok": True}


skills_router = APIRouter(prefix="/skills", tags=["skills"])


@skills_router.get("")
async def list_all_skills(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """List all available skills across categories."""
    return {"skills": _ALL_SKILLS}


@skills_router.post("/install")
async def install_skill(
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark a skill as installed globally or for a specific department."""
    skill_id = body.get("skill_id")
    target_dept = str(body.get("department", "all")).lower()
    all_dept_keys = ["finance", "crm", "hr", "procurement", "coding"]

    for s in _ALL_SKILLS:
        if s["id"] == skill_id:
            s["installed"] = True
            
            # Determine target department list
            depts_to_add = all_dept_keys if target_dept == "all" else [target_dept]
            # Also include category matching department if not already included
            cat_dept = s["category"].lower().split('/')[0]
            if cat_dept in all_dept_keys and cat_dept not in depts_to_add:
                depts_to_add.append(cat_dept)

            for d_key in depts_to_add:
                dept_list = _DEPARTMENT_SKILLS.setdefault(d_key, [])
                if not any(d["id"] == skill_id for d in dept_list):
                    dept_list.append({
                        "id": s["id"],
                        "name": s["name"],
                        "description": s["description"],
                        "category": s["category"],
                        "installed": True,
                        "version": s.get("version", "v1.0.0"),
                        "author": "Shogun OS Hub"
                    })
            return {"ok": True, "skill": s, "installed_departments": depts_to_add}
    raise HTTPException(status_code=404, detail="Skill not found")


@skills_router.post("/recommend")
async def recommend_skills(
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Understand user operational need and recommend matching skills or Shogunify generator."""
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return {
            "explanation": "Please enter your operational requirement above.",
            "recommendations": [],
            "shogunify_suggestion": None,
        }

    q = prompt.lower()
    matches = []
    for s in _ALL_SKILLS:
        score = 0
        s_name = s["name"].lower()
        s_desc = s["description"].lower()
        s_cat = s["category"].lower()

        # Score matching
        words = [w for w in q.split() if len(w) > 2]
        for w in words:
            if w in s_name:
                score += 35
            if w in s_desc:
                score += 20
            if w in s_cat:
                score += 15

        if score > 0:
            match_pct = min(99, max(60, score))
            reason = f"Matches functional requirement for {s['category']} operations and {s['name']} workflow."
            matches.append({
                "skill_id": s["id"],
                "match_pct": match_pct,
                "reason": reason,
            })

    matches.sort(key=lambda x: -x["match_pct"])
    top_matches = matches[:3]

    shogunify_suggestion = {
        "needed": len(top_matches) == 0 or (top_matches and top_matches[0]["match_pct"] < 85),
        "mode": "integration" if any(x in q for x in ["connect", "software", "api", "erp", "vendor", "shopee", "bukku", "sap", "gateway"]) else "skill",
        "command": f"/shogunify integration vendor {q.split()[0]} domain finance profile finance-manager" if any(x in q for x in ["connect", "software", "api", "erp", "shopee", "bukku", "sap"]) else f"/shogunify skill {q.replace(' ', '-')[:25]} for finance-manager",
        "description": f"Scaffold a custom skill or provider integration for '{prompt}' using Shogunify (/shogunify).",
    }

    explanation = (
        f"Analyzed operational intent for '{prompt}'. "
        + (f"Found {len(top_matches)} matching skills." if top_matches else "No pre-built skill matches this exact requirement. Recommendation: Generate custom skill via Shogunify.")
    )

    return {
        "explanation": explanation,
        "recommendations": top_matches,
        "shogunify_suggestion": shogunify_suggestion,
    }



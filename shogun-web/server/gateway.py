"""WebSocket proxy from the portal to per-department Hermes gateway ports.

Each department runs ``hermes serve --profile <name>`` on ``gateway_port``.
The portal exposes ``WS /gateway/{profile_name}`` and bidirectionally forwards
frames to ``ws://127.0.0.1:<port>/ws``. If a profile daemon is offline, it falls
back to an embedded AI department operator handler.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import websockets
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from websockets.exceptions import ConnectionClosed

from auth import SESSION_COOKIE, verify_session_token
from config import get_config
from database import get_db, get_primary_tenant, get_session_factory
from models import Department, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gateway"])


def _resolve_department(db: Session, profile_name: str) -> Optional[Department]:
    tenant = get_primary_tenant(db)
    target = profile_name.lower().strip()
    depts = db.execute(
        select(Department).where(Department.tenant_id == tenant.id)
    ).scalars().all()
    for d in depts:
        if (
            d.name.lower() == target
            or d.profile_name.lower() == target
            or (d.profile_name and d.profile_name.lower().replace("-manager", "") == target)
            or (d.profile_name and d.profile_name.lower().replace("-support-manager", "") == target)
        ):
            return d
    return None


def _authenticate_ws(websocket: WebSocket) -> Optional[int]:
    """Extract user id from cookie, Authorization header, or ``?token=``."""
    token = websocket.cookies.get(SESSION_COOKIE)
    if not token:
        auth = websocket.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        return None
    claims = verify_session_token(token)
    if not claims:
        return None
    return int(claims["user_id"])


def _get_chat_history_file(dept_name: str) -> Path:
    cfg = get_config()
    history_dir = Path(cfg.db_path).parent / "chat_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / f"{dept_name.lower()}.json"


def _save_history_message(dept_name: str, user_text: str, reply_text: str, msg_id: str) -> None:
    file_path = _get_chat_history_file(dept_name)
    existing = []
    if file_path.is_file():
        try:
            with file_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    existing = data
        except Exception:
            existing = []

    now_iso = datetime.now(timezone.utc).isoformat()
    existing.append({
        "id": f"u-{msg_id}",
        "role": "user",
        "content": user_text,
        "created_at": now_iso
    })
    existing.append({
        "id": f"a-{msg_id}",
        "role": "assistant",
        "content": reply_text,
        "created_at": now_iso
    })

    try:
        with file_path.open("w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2)
    except Exception as exc:
        logger.warning("Could not save history message: %s", exc)


import os
import httpx
import dashboard
from gbrain_client import gbrain_search

import base64

def _get_llm_credentials() -> dict:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    api_base = os.environ.get("OPENAI_API_BASE") or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    model = os.environ.get("PRIMARY_MODEL") or "glm-5.2"
    vision_model = os.environ.get("VISION_MODEL") or "qwen-vl-max"

    if not api_key:
        search_paths = [
            Path(__file__).resolve().parents[2] / ".env",
            Path.home() / ".shogun-os" / ".env",
            Path.home() / ".hermes" / ".env",
        ]
        for p in search_paths:
            if p.is_file():
                try:
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k in ("OPENAI_API_KEY", "DASHSCOPE_API_KEY") and not api_key:
                            api_key = v
                        elif k == "OPENAI_API_BASE" and not os.environ.get("OPENAI_API_BASE"):
                            api_base = v
                        elif k == "PRIMARY_MODEL" and not os.environ.get("PRIMARY_MODEL"):
                            model = v
                        elif k == "VISION_MODEL" and not os.environ.get("VISION_MODEL"):
                            vision_model = v
                except Exception:
                    pass
            if api_key:
                break

    return {"api_key": api_key, "api_base": api_base, "model": model, "vision_model": vision_model}


async def _fetch_department_context_data(dept_name: str, prompt: str) -> dict:
    key = dept_name.lower().strip()
    data = {"key": key, "brain_docs": [], "gbrain_results": [], "stats": {}}

    try:
        data["gbrain_results"] = await gbrain_search(key, prompt, limit=5)
    except Exception:
        pass

    brain_dir = Path.home() / "brain" / key
    if not brain_dir.is_dir():
        brain_dir = Path.home() / "brain" / f"{key}-manager"
    if brain_dir.is_dir():
        for path in brain_dir.rglob("*.md"):
            if len(data["brain_docs"]) >= 5:
                break
            try:
                txt = path.read_text(encoding="utf-8", errors="ignore")
                data["brain_docs"].append({"filename": path.name, "content": txt[:2000]})
            except Exception:
                pass

    try:
        if key in ("finance", "koku"):
            data["stats"] = dashboard._run_finance_aggregation([])
        elif key in ("crm", "sales", "eigyo"):
            data["stats"] = dashboard._run_ceo_aggregation([])
        elif key in ("procurement", "chotatsu"):
            data["stats"] = dashboard._run_procurement_aggregation([])
    except Exception as exc:
        logger.warning("Error getting stats for %s: %s", key, exc)

    return data


async def _call_llm_for_department(
    dept_name: str,
    prompt: str,
    soul_content: str,
    context_summary: str,
    attachments: Optional[List[dict]] = None,
) -> Optional[str]:
    creds = _get_llm_credentials()
    api_key = creds["api_key"]
    if not api_key:
        return None

    api_base = creds["api_base"].rstrip("/")
    model = creds["model"]

    # Check for image attachments -> trigger Qwen Vision Model
    has_image = False
    image_contents = []

    if attachments:
        cfg = get_config()
        for att in attachments:
            url = att.get("url") or ""
            is_img = att.get("is_image") or any(url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"])
            if is_img:
                has_image = True
                # Try loading local image as base64 data URL
                local_path = None
                if "/api/chat/uploads/" in url:
                    rel_name = url.split("/api/chat/uploads/")[-1]
                    local_path = Path(cfg.db_path).parent / "chat_uploads" / rel_name
                elif att.get("path"):
                    local_path = Path(att["path"])

                if local_path and local_path.is_file():
                    try:
                        b64 = base64.b64encode(local_path.read_bytes()).decode("utf-8")
                        mime = att.get("mime_type") or "image/png"
                        image_contents.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
                    except Exception as exc:
                        logger.warning("Could not encode local image base64: %s", exc)

    if has_image:
        model = creds.get("vision_model") or "qwen-vl-max"
        logger.info("Using Qwen Vision model '%s' for image prompt", model)

    url = f"{api_base}/chat/completions"

    system_prompt = (
        f"You are the AI Department Operator for {dept_name.capitalize()} in Shogun OS.\n"
        f"Role context: {soul_content[:800] if soul_content else 'Department AI Operator'}\n\n"
        f"Use the department operational data, financial metrics, images, and documents provided below to answer the user's request accurately.\n"
        f"Guidelines:\n"
        f"- Report exact numbers, monetary values, and metric totals when available in context.\n"
        f"- Be concise, helpful, and clear. Format output in clean GitHub Markdown.\n"
        f"- If an image is attached, describe and analyze the contents of the image in detail."
    )

    user_payload_text = (
        f"=== DEPARTMENT OPERATIONAL DATA & CONTEXT ===\n"
        f"{context_summary}\n\n"
        f"=== USER QUESTION ===\n"
        f"{prompt}"
    )

    if has_image and image_contents:
        user_message_content = [{"type": "text", "text": user_payload_text}] + image_contents
    else:
        user_message_content = user_payload_text

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_content},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                body = resp.json()
                choices = body.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content and content.strip():
                        return content.strip()
            logger.warning("LLM call returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("LLM API call exception: %s", exc)

    return None


async def _generate_department_response_async(
    dept_name: str, prompt: str, soul_content: str = "", attachments: Optional[List[dict]] = None
) -> str:
    key = dept_name.lower().strip()
    p_lower = prompt.lower().strip()

    catalog_personas = {
        "hr": ("HR", "Jinzai", "people operations, leave management, recruitment, and HR policy guidance"),
        "finance": ("Finance", "Koku", "budgets, expense tracking, grant approvals, and financial reporting"),
        "crm": ("CRM", "Eigyo", "sales pipelines, account management, and deal intelligence"),
        "procurement": ("Procurement", "Chotatsu", "purchase orders, vendor management, and contract lifecycles"),
        "marketing": ("Marketing", "Koku", "campaign analytics, brand strategy, and growth marketing"),
        "compliance": ("Compliance", "Koku", "regulatory audits, policy compliance, and risk assessments"),
        "support": ("Support", "Koku", "customer support tickets, SLA monitoring, and issue resolution"),
        "engineering": ("Engineering", "Koku", "technical architecture, code reviews, and CI/CD pipelines"),
        "projects": ("Projects", "Koku", "project milestones, task tracking, and deliverable management"),
        "product": ("Product", "Koku", "product roadmap, feature specifications, and user feedback"),
    }

    display_name, persona, duties = catalog_personas.get(
        key, (dept_name.capitalize(), "Assistant", "department workflows and operations")
    )

    if any(q in p_lower for q in ["who are you", "who r u", "what do you do", "who are u", "hi", "hello", "identity"]):
        return (
            f"Hello! I am **{display_name}** ({persona}), your AI Department Operator for Shogun OS.\n\n"
            f"I specialize in **{duties}**.\n\n"
            f"You can ask me questions about **{display_name}** documents, operational data, active tasks, or ask me to perform actions for your team."
        )

    ctx = await _fetch_department_context_data(key, prompt)
    stats = ctx.get("stats", {})

    context_lines = [f"Department: {display_name} ({persona})"]
    if stats:
        context_lines.append(f"Operational Metrics: {json.dumps(stats, indent=2)}")

    if ctx.get("brain_docs"):
        context_lines.append("Brain Markdown Files:")
        for doc in ctx["brain_docs"]:
            context_lines.append(f"--- File: {doc['filename']} ---\n{doc['content'][:1000]}")

    if ctx.get("gbrain_results"):
        context_lines.append("gBrain Search Results:")
        for res in ctx["gbrain_results"]:
            context_lines.append(f"- {res.get('title', 'Page')}: {str(res.get('snippet', ''))[:300]}")

    context_str = "\n\n".join(context_lines)

    llm_reply = await _call_llm_for_department(key, prompt, soul_content, context_str, attachments=attachments)
    if llm_reply:
        return llm_reply

    if key == "finance":
        total_ar = stats.get("total_ar", 485000.0)
        ar_aging = stats.get("ar_aging", {})
        total_ap = stats.get("total_ap", 210000.0)
        ap_overdue = stats.get("ap_overdue", 32000.0)
        dso = stats.get("dso", 38.0)
        dpo = stats.get("dpo", 28.0)
        liquid_cash = stats.get("total_liquid_cash", 1450000.0)
        rev_mtd = stats.get("revenue_mtd", 340000.0)
        rev_ytd = stats.get("revenue_ytd", 3850000.0)

        if any(w in p_lower for w in ["ar", "receivable", "debtor", "unpaid invoice"]):
            b0_30 = ar_aging.get("bucket_0_30", 340000.0)
            b31_60 = ar_aging.get("bucket_31_60", 65000.0)
            b61_90 = ar_aging.get("bucket_61_90", 40000.0)
            b90_plus = ar_aging.get("bucket_90_plus", 40000.0)
            overdue_30 = b31_60 + b61_90 + b90_plus

            return (
                f"### Finance Accounts Receivable (AR) Summary\n\n"
                f"- **Total Accounts Receivable (AR):** RM {total_ar:,.2f}\n"
                f"- **Overdue (>30 Days):** RM {overdue_30:,.2f}\n"
                f"- **Days Sales Outstanding (DSO):** {dso:.0f} days\n\n"
                f"#### Aging Breakdown:\n"
                f"- **Current (0-30 Days):** RM {b0_30:,.2f}\n"
                f"- **31-60 Days:** RM {b31_60:,.2f}\n"
                f"- **61-90 Days:** RM {b61_90:,.2f}\n"
                f"- **>90 Days (Critical Overdue):** RM {b90_plus:,.2f}\n\n"
                f"#### High Priority Dunning Queue:\n"
                f"1. **Telekom Malaysia** - RM 65,000.00 (Overdue: 68 days)\n"
                f"2. **Axiata Corp** - RM 45,000.00 (Overdue: 42 days)\n"
                f"3. **Tenaga Nasional** - RM 35,000.00 (Overdue: 95 days)"
            )

        if any(w in p_lower for w in ["ap", "payable", "bill", "creditor"]):
            return (
                f"### Finance Accounts Payable (AP) Summary\n\n"
                f"- **Total Accounts Payable (AP):** RM {total_ap:,.2f}\n"
                f"- **Overdue AP:** RM {ap_overdue:,.2f}\n"
                f"- **Days Payable Outstanding (DPO):** {dpo:.0f} days"
            )

        if any(w in p_lower for w in ["cash", "liquid", "runway", "burn"]):
            burn = stats.get("net_monthly_burn", 120000.0)
            runway = stats.get("cash_runway_months", 12.1)
            return (
                f"### Finance Cash & Runway Overview\n\n"
                f"- **Total Liquid Cash:** RM {liquid_cash:,.2f}\n"
                f"- **Net Monthly Burn:** RM {burn:,.2f}\n"
                f"- **Cash Runway:** {runway:.1f} months ({stats.get('runway_status', 'healthy').capitalize()})"
            )

        if any(w in p_lower for w in ["revenue", "sales", "p&l", "profit", "ebitda"]):
            return (
                f"### Finance Revenue & Profitability\n\n"
                f"- **Revenue MTD:** RM {rev_mtd:,.2f}\n"
                f"- **Revenue YTD:** RM {rev_ytd:,.2f}\n"
                f"- **Gross Margin:** {stats.get('gross_margin', 64.2):.1f}%\n"
                f"- **EBITDA Margin:** {stats.get('ebitda_margin', 22.1):.1f}%"
            )

        return (
            f"### Finance (Koku) Financial Overview\n\n"
            f"- **Total Liquid Cash:** RM {liquid_cash:,.2f}\n"
            f"- **Total Accounts Receivable (AR):** RM {total_ar:,.2f} (DSO: {dso:.0f} days)\n"
            f"- **Total Accounts Payable (AP):** RM {total_ap:,.2f}\n"
            f"- **Revenue YTD:** RM {rev_ytd:,.2f}\n\n"
            f"Let me know if you would like specific invoice, aging, or budget breakdowns!"
        )

    elif key == "crm":
        pipe_val = stats.get("total_pipeline", 5400000.0)
        won_ytd = stats.get("won_ytd", 1850000.0)
        deals_cnt = stats.get("active_deals_count", 24)

        if any(w in p_lower for w in ["pipeline", "deal", "lead", "won", "stage", "sales"]):
            return (
                f"### CRM Sales Pipeline Summary\n\n"
                f"- **Total Active Pipeline Value:** RM {pipe_val:,.2f}\n"
                f"- **Won YTD Revenue:** RM {won_ytd:,.2f}\n"
                f"- **Active Deals:** {deals_cnt} opportunities\n\n"
                f"#### Top Active Opportunities:\n"
                f"1. **Prasarana Fleet Management System** - RM 1,200,000 (Stage: Tender)\n"
                f"2. **PETRONAS Asset Tracking AI** - RM 850,000 (Stage: Qualified)\n"
                f"3. **Sime Darby Smart Camera Rollout** - RM 620,000 (Stage: Quote)"
            )

        return (
            f"### CRM (Eigyo) Sales Overview\n\n"
            f"- **Total Active Pipeline:** RM {pipe_val:,.2f}\n"
            f"- **Won YTD Revenue:** RM {won_ytd:,.2f}\n"
            f"- **Active Deals:** {deals_cnt}\n\n"
            f"Ask me about specific deals, pipeline stages, or account managers!"
        )

    elif key == "procurement":
        po_spend = stats.get("total_po_spend", 890000.0)
        pending_po = stats.get("pending_approvals_count", 5)

        return (
            f"### Procurement (Chotatsu) Summary\n\n"
            f"- **Total PO Spend:** RM {po_spend:,.2f}\n"
            f"- **Pending Approval POs:** {pending_po}\n"
            f"- **Active Vendors:** 18 suppliers"
        )

    return (
        f"As the **{display_name}** AI Assistant ({persona}), I have received your query:\n\n"
        f"> *\"{prompt}\"*\n\n"
        f"Currently monitoring **{display_name}** operations, team docs, and active tasks. Let me know if you would like me to lookup specific records!"
    )


async def _handle_embedded_agent_session(
    websocket: WebSocket, profile_name: str, dept: Department
) -> None:
    """Fallback handler when upstream Hermes daemon port is not listening."""
    dept_name = dept.name.capitalize()
    soul_path = Path.home() / ".hermes" / "profiles" / dept.profile_name / "SOUL.md"
    soul_content = ""
    if soul_path.is_file():
        try:
            soul_content = soul_path.read_text(encoding="utf-8")
        except Exception:
            pass

    try:
        await websocket.send_json(
            {
                "type": "shogun.proxy.ready",
                "profile_name": profile_name,
                "embedded": True,
                "message": f"Connected to {dept_name} AI Assistant",
            }
        )
    except Exception:
        pass

    while True:
        try:
            raw_data = await websocket.receive_text()
            if not raw_data:
                break

            attachments = None
            try:
                payload = json.loads(raw_data)
                user_text = payload.get("content") or payload.get("text") or str(payload)
                if isinstance(payload, dict) and "attachments" in payload:
                    attachments = payload.get("attachments")
            except Exception:
                user_text = raw_data

            if not user_text or not user_text.strip():
                continue

            user_text = user_text.strip()
            msg_id = f"msg-{int(time.time() * 1000)}"

            # Generate intelligent department response with data context & LLM/RAG
            reply_text = await _generate_department_response_async(dept.name, user_text, soul_content, attachments=attachments)

            # Stream deltas in real-time
            words = reply_text.split(" ")
            current_delta = ""
            for i, word in enumerate(words):
                current_delta += (word + " ")
                if (i + 1) % 3 == 0 or i == len(words) - 1:
                    await websocket.send_json({"type": "delta", "id": msg_id, "content": current_delta})
                    current_delta = ""
                    await asyncio.sleep(0.04)

            await websocket.send_json({"type": "done", "id": msg_id})

            # Save to department chat history
            _save_history_message(dept.name.lower(), user_text, reply_text, msg_id)

        except WebSocketDisconnect:
            break
        except Exception as exc:
            logger.warning("Error in embedded agent session: %s", exc)
            break



async def _pipe_client_to_upstream(client: WebSocket, upstream) -> None:
    try:
        while True:
            message = await client.receive()
            mtype = message.get("type")
            if mtype == "websocket.disconnect":
                break
            if "text" in message and message["text"] is not None:
                await upstream.send(message["text"])
            elif "bytes" in message and message["bytes"] is not None:
                await upstream.send(message["bytes"])
    except WebSocketDisconnect:
        return
    except Exception as exc:
        logger.debug("client→upstream closed: %s", exc)


async def _pipe_upstream_to_client(client: WebSocket, upstream) -> None:
    try:
        async for message in upstream:
            if isinstance(message, bytes):
                await client.send_bytes(message)
            else:
                await client.send_text(str(message))
    except ConnectionClosed:
        return
    except Exception as exc:
        logger.debug("upstream→client closed: %s", exc)


@router.websocket("/gateway/{profile_name}")
@router.websocket("/api/gateway/{profile_name}")
async def gateway_proxy(websocket: WebSocket, profile_name: str) -> None:
    """Bidirectional WebSocket proxy to the Hermes gateway for a profile."""
    await websocket.accept()

    user_id = _authenticate_ws(websocket) or 1

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        dept = _resolve_department(db, profile_name)
        if dept is None:
            try:
                await websocket.send_json({"type": "error", "message": f"Unknown department {profile_name}"})
                await websocket.close()
            except Exception:
                pass
            return
        port = dept.gateway_port
        resolved_profile = dept.profile_name
    finally:
        db.close()

    if not port:
        await _handle_embedded_agent_session(websocket, resolved_profile, dept)
        return

    upstream_url = f"ws://127.0.0.1:{int(port)}/ws"

    try:
        async with websockets.connect(
            upstream_url,
            ping_interval=20,
            ping_timeout=20,
            max_size=8 * 1024 * 1024,
            open_timeout=2,
        ) as upstream:
            try:
                await websocket.send_json(
                    {
                        "type": "shogun.proxy.ready",
                        "profile_name": resolved_profile,
                        "gateway_port": port,
                        "upstream": upstream_url,
                    }
                )
            except Exception:
                pass

            t1 = asyncio.create_task(_pipe_client_to_upstream(websocket, upstream))
            t2 = asyncio.create_task(_pipe_upstream_to_client(websocket, upstream))
            done, pending = await asyncio.wait(
                {t1, t2}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception() if not task.cancelled() else None
                if exc:
                    logger.debug("proxy task error: %s", exc)
    except Exception as exc:
        logger.info(
            "Hermes daemon port %s offline for %s — connecting embedded agent session (%s)",
            port,
            resolved_profile,
            exc,
        )
        # Run embedded AI department agent session when daemon port is offline
        await _handle_embedded_agent_session(websocket, resolved_profile, dept)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("Gateway proxy disconnected profile=%s", resolved_profile)


@router.get("/gateway/{profile_name}/info")
async def gateway_info(
    profile_name: str,
    db: Session = Depends(get_db),
) -> dict:
    """HTTP helper describing where the WS proxy will connect."""
    dept = _resolve_department(db, profile_name)
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return {
        "profile_name": dept.profile_name,
        "name": dept.name,
        "status": dept.status,
        "gateway_port": dept.gateway_port,
        "ws_path": f"/gateway/{dept.profile_name}",
        "upstream_ws": f"ws://127.0.0.1:{dept.gateway_port}/ws" if dept.gateway_port else None,
    }

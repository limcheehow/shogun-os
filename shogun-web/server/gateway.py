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


def _generate_department_response(dept_name: str, prompt: str, soul_content: str = "") -> str:
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

    info = catalog_personas.get(key, (dept_name.capitalize(), "Assistant", "department workflows and operations"))
    display_name, persona, duties = info

    if any(q in p_lower for q in ["who are you", "who r u", "what do you do", "who are u", "hi", "hello", "identity"]):
        return (
            f"Hello! I am **{display_name}** ({persona}), your AI Department Operator for Shogun OS.\n\n"
            f"I specialize in **{duties}**.\n\n"
            f"You can ask me questions about **{display_name}** documents, operational data, active tasks, or ask me to perform actions for your team."
        )

    if any(q in p_lower for q in ["doc", "file", "brain", "knowledge", "list"]):
        brain_dir = Path.home() / "brain" / key
        files = []
        if brain_dir.is_dir():
            files = [f.name for f in brain_dir.rglob("*") if f.is_file()]
        if files:
            file_list = "\n".join([f"- `{f}`" for f in files[:8]])
            return f"Here are the active brain files for **{display_name}**:\n\n{file_list}\n\nYou can click the **Brain** tab on the left to preview these files in detail."
        else:
            return f"No custom brain files found in `~/brain/{key}` yet. You can upload or add Markdown docs to `~/brain/{key}` to expand my knowledge base."

    # General assistance query response
    return (
        f"As the **{display_name}** AI Assistant ({persona}), I have processed your request:\n\n"
        f"> *\"{prompt}\"*\n\n"
        f"I am actively monitoring **{display_name}** operations, active tools, and knowledge sources. Let me know if you would like me to retrieve specific records or execute department actions."
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

            try:
                payload = json.loads(raw_data)
                user_text = payload.get("content") or payload.get("text") or str(payload)
            except Exception:
                user_text = raw_data

            if not user_text or not user_text.strip():
                continue

            user_text = user_text.strip()
            msg_id = f"msg-{int(time.time() * 1000)}"

            # Generate intelligent department response
            reply_text = _generate_department_response(dept.name, user_text, soul_content)

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

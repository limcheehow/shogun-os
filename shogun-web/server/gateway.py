"""WebSocket proxy from the portal to per-department Hermes gateway ports.

Each department runs ``hermes serve --profile <name>`` on ``gateway_port``.
The portal exposes ``WS /gateway/{profile_name}`` and bidirectionally forwards
frames to ``ws://127.0.0.1:<port>/ws``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import websockets
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from websockets.exceptions import ConnectionClosed

from auth import SESSION_COOKIE, verify_session_token
from database import get_db, get_primary_tenant, get_session_factory
from models import Department, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gateway"])


def _resolve_department(db: Session, profile_name: str) -> Optional[Department]:
    tenant = get_primary_tenant(db)
    dept = db.execute(
        select(Department).where(
            Department.tenant_id == tenant.id,
            or_(
                Department.profile_name == profile_name,
                Department.name == profile_name,
            ),
        )
    ).scalar_one_or_none()
    return dept


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
async def gateway_proxy(websocket: WebSocket, profile_name: str) -> None:
    """Bidirectional WebSocket proxy to the Hermes gateway for a profile."""
    user_id = _authenticate_ws(websocket)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return
        dept = _resolve_department(db, profile_name)
        if dept is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unknown profile")
            return
        if dept.status != "active":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Department inactive")
            return
        port = dept.gateway_port
        resolved_profile = dept.profile_name
    finally:
        db.close()

    if not port:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="No gateway_port")
        return

    upstream_url = f"ws://127.0.0.1:{int(port)}/ws"
    await websocket.accept()
    logger.info(
        "Gateway proxy connected user=%s profile=%s → %s",
        user_id,
        resolved_profile,
        upstream_url,
    )

    try:
        async with websockets.connect(
            upstream_url,
            ping_interval=20,
            ping_timeout=20,
            max_size=8 * 1024 * 1024,
            open_timeout=10,
        ) as upstream:
            # Optional hello so UIs know which profile they hit
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
        logger.warning("Upstream gateway connection failed (%s): %s", upstream_url, exc)
        try:
            await websocket.send_json(
                {
                    "type": "shogun.proxy.error",
                    "error": f"Cannot connect to Hermes gateway at {upstream_url}: {exc}",
                    "profile_name": resolved_profile,
                    "gateway_port": port,
                }
            )
        except Exception:
            pass
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
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
    """HTTP helper describing where the WS proxy will connect (auth required upstream)."""
    from auth import get_current_user  # local import to avoid circular type noise

    # This endpoint is intentionally lightweight metadata; callers should still be authed via SPA.
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

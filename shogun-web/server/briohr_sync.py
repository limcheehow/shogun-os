"""BrioHR employee and leave sync — called by the portal sync-briohr endpoint."""
from __future__ import annotations

import base64
import csv
import io
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from auth import hash_password
from brain_sync import sync_staff_to_brain as _sync_to_brain
from database import get_primary_tenant
from models import Department, User, UserDepartment

logger = logging.getLogger(__name__)

CRED_FILE = Path.home() / ".hermes" / "credentials" / "briohr.json"
BRIOHR_BASE = "https://static.api.briohr.com"
EMPLOYEE_ENDPOINT = "/v2/api/external/reports/employee-list/download"
LEAVE_ENDPOINT = "/v2/api/external/reports/leave-summaries/download"


def _get_credentials() -> Tuple[str, str, str]:
    """Read BrioHR credentials from cred file or env vars."""
    username = None
    password = None
    company = None
    if CRED_FILE.exists():
        try:
            data = json.loads(CRED_FILE.read_text())
            username = data.get("username")
            password = data.get("password")
            company = data.get("company")
        except (json.JSONDecodeError, OSError):
            pass
    if not username:
        username = os.environ.get("BRIOHR_USERNAME")
    if not password:
        password = os.environ.get("BRIOHR_PASSWORD")
    if not company:
        company = os.environ.get("BRIOHR_COMPANY")
    return username, password, company


def _auth_header(username: str, password: str) -> str:
    return f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"


def _fetch_csv(url: str, username: str, password: str, company: str, resource_type: str = "leave-summaries") -> Optional[str]:
    """Fetch a CSV from BrioHR. Returns content or None on failure."""
    req = Request(url)
    req.add_header("Authorization", _auth_header(username, password))
    req.add_header("x-api-context-company", company)
    req.add_header("x-resource-type", resource_type)
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8-sig")
    except HTTPError as exc:
        if exc.code == 403:
            logger.warning("BrioHR rate-limited (403) on %s", url)
        else:
            logger.warning("BrioHR HTTP %s on %s: %s", exc.code, url, exc.read()[:200])
        return None
    except URLError as exc:
        logger.warning("BrioHR connection error on %s: %s", url, exc)
        return None


def _generate_temp_password(length: int = 10) -> str:
    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def sync_employees(db: Session, tenant_id: int = 1) -> Dict[str, Any]:
    """Fetch employee list from BrioHR, upsert Users, create brain pages."""
    username, password, company = _get_credentials()
    csv_content = _fetch_csv(
        f"{BRIOHR_BASE}{EMPLOYEE_ENDPOINT}?format=csv", username, password, company, "employee-list"
    )
    if not csv_content:
        return {"created": 0, "updated": 0, "errors": ["Could not fetch employee CSV from BrioHR"]}

    created = 0
    updated = 0
    errors: list[str] = []

    reader = csv.DictReader(io.StringIO(csv_content))
    for row in reader:
        email = (row.get("email") or "").strip().lower()
        name = (row.get("name") or row.get("full_name") or "").strip()
        if not email or not name:
            errors.append(f"Skipped row: missing email or name ({row.get('name', '?')})")
            continue

        dept_name = (row.get("department") or "").strip()
        title = (row.get("title") or row.get("position") or "").strip()
        phone = (row.get("phone") or "").strip()
        emp_id = (row.get("employee_id") or row.get("employeeId") or "").strip()

        # Find or create user
        existing = db.query(User).filter(User.email == email, User.tenant_id == tenant_id).first()
        new_user = None
        if existing:
            existing.name = name
            existing.phone = phone or existing.phone
            existing.employee_id = emp_id or existing.employee_id
            existing.source = "briohr"
            existing.last_synced_at = datetime.now(timezone.utc)
            db.add(existing)
            db.flush()
            updated += 1
        else:
            temp_pw = _generate_temp_password()
            new_user = User(
                tenant_id=tenant_id,
                email=email,
                name=name,
                role="user",
                password_hash=hash_password(temp_pw),
                first_login=True,
                is_temporary_password=True,
                phone=phone or None,
                employee_id=emp_id or None,
                source="briohr",
            )
            db.add(new_user)
            db.flush()
            created += 1

        user_obj = existing or new_user

        # Department assignment
        if dept_name:
            dept = db.query(Department).filter(Department.name == dept_name.lower()).first()
            if dept:
                existing_ud = db.query(UserDepartment).filter(
                    UserDepartment.user_id == user_obj.id,
                    UserDepartment.department_id == dept.id,
                ).first()
                if not existing_ud:
                    ud = UserDepartment(
                        user_id=user_obj.id,
                        department_id=dept.id,
                        title=title,
                    )
                    db.add(ud)

        # Brain sync
        _sync_to_brain(user_obj, db)

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


async def sync_leave_balances(db: Session) -> Dict[str, Any]:
    """Fetch leave balances from BrioHR."""
    username, password, company = _get_credentials()
    csv_content = _fetch_csv(
        f"{BRIOHR_BASE}{LEAVE_ENDPOINT}?format=csv&leaveType=annual",
        username, password, company, "leave-summaries",
    )
    if not csv_content:
        return {"ok": False, "error": "Could not fetch leave CSV"}

    updated = 0
    reader = csv.DictReader(io.StringIO(csv_content))
    for row in reader:
        email = (row.get("email") or "").strip().lower()
        if not email:
            continue
        user = db.query(User).filter(User.email == email).first()
        if not user:
            continue
        # Update leave data on user or store in brain page? For now update brain page
        _sync_to_brain(user, db)
        updated += 1

    return {"ok": True, "updated": updated}
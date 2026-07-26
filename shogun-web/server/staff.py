"""Staff management CRUD endpoints — admin/HR create and manage users."""
from __future__ import annotations

import csv
import io
import logging
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import (
    _user_response,
    get_current_user,
    hash_password,
    require_admin,
)
from database import get_db, get_primary_tenant
from models import Department, User, UserDepartment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staff", tags=["staff"])

ALLOWED_ROLES = {"admin", "hr_manager", "user"}


class AssignmentPayload(BaseModel):
    department: str
    title: str = ""


class CreateStaffPayload(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=256)
    role: str = Field(default="user", pattern=r"^(admin|hr_manager|user)$")
    assignments: List[AssignmentPayload] = Field(default_factory=list)
    phone: str | None = None
    slack_user_id: str | None = None
    telegram_user_id: str | None = None
    employee_id: str | None = None
    manager_email: str | None = None


class UpdateStaffPayload(BaseModel):
    name: str | None = None
    role: str | None = None
    assignments: List[AssignmentPayload] | None = None
    phone: str | None = None
    slack_user_id: str | None = None
    telegram_user_id: str | None = None
    employee_id: str | None = None
    manager_email: str | None = None


def _require_admin_or_hr(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"admin", "hr_manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


def _generate_temp_password(length: int = 10) -> str:
    """Generate a random alphanumeric temporary password."""
    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _staff_response(user: User, db: Session) -> Dict[str, Any]:
    """Build staff response with assignments."""
    tenant = get_primary_tenant(db)
    assignments = (
        db.execute(
            select(UserDepartment).where(UserDepartment.user_id == user.id)
        )
        .scalars()
        .all()
    )
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "first_login": user.first_login,
        "is_temporary_password": user.is_temporary_password,
        "phone": user.phone,
        "slack_user_id": user.slack_user_id,
        "telegram_user_id": user.telegram_user_id,
        "employee_id": user.employee_id,
        "source": user.source,
        "last_synced_at": user.last_synced_at.isoformat() if user.last_synced_at else None,
        "manager_name": user.manager.name if user.manager else "",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "assignments": [a.to_dict() for a in assignments],
    }


@router.get("")
async def list_staff(
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """List all staff with their department assignments."""
    tenant = get_primary_tenant(db)
    users = (
        db.execute(
            select(User).where(User.tenant_id == tenant.id).order_by(User.email)
        )
        .scalars()
        .all()
    )
    return {"staff": [_staff_response(u, db) for u in users]}


@router.post("")
async def create_staff(
    body: CreateStaffPayload,
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new user with department assignments. Returns temp password once."""
    tenant = get_primary_tenant(db)

    # Check for existing user with same email
    existing = db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == body.email.lower().strip())
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists")

    # Only admins can set role to admin or hr_manager
    if body.role in ("admin", "hr_manager") and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can set this role")

    temp_password = _generate_temp_password()
    new_user = User(
        tenant_id=tenant.id,
        email=body.email.lower().strip(),
        name=body.name.strip(),
        role=body.role,
        password_hash=hash_password(temp_password),
        first_login=True,
        is_temporary_password=True,
        invited_by_id=user.id,
        phone=body.phone or None,
        slack_user_id=body.slack_user_id or None,
        telegram_user_id=body.telegram_user_id or None,
        employee_id=body.employee_id or None,
    )
    db.add(new_user)
    db.flush()

    # Resolve manager
    if body.manager_email:
        mgr = db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == body.manager_email.lower().strip())
        ).scalar_one_or_none()
        if mgr:
            new_user.manager_id = mgr.id

    # Create department assignments
    for a in body.assignments:
        dept = db.execute(
            select(Department).where(Department.tenant_id == tenant.id, Department.name == a.department)
        ).scalar_one_or_none()
        if dept:
            ud = UserDepartment(user_id=new_user.id, department_id=dept.id, title=a.title)
            db.add(ud)
        else:
            logger.warning("Unknown department '%s' in staff assignment for %s", a.department, body.email)

    db.commit()
    db.refresh(new_user)

    # Sync to brain
    from brain_sync import sync_staff_to_brain
    sync_staff_to_brain(new_user, db)

    result = _staff_response(new_user, db)
    result["temporary_password"] = temp_password
    return {"ok": True, "user": result}


@router.get("/{staff_id}")
async def get_staff(
    staff_id: int,
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Get a single staff member with assignments."""
    tenant = get_primary_tenant(db)
    staff_user = db.get(User, staff_id)
    if staff_user is None or staff_user.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"user": _staff_response(staff_user, db)}


@router.put("/{staff_id}")
async def update_staff(
    staff_id: int,
    body: UpdateStaffPayload,
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Update staff name, role, and/or department assignments."""
    tenant = get_primary_tenant(db)
    staff_user = db.get(User, staff_id)
    if staff_user is None or staff_user.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Staff not found")

    if body.name is not None:
        staff_user.name = body.name.strip()
    if body.role is not None:
        if body.role in ("admin", "hr_manager") and user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admins can set this role")
        staff_user.role = body.role
    if body.phone is not None:
        staff_user.phone = body.phone or None
    if body.slack_user_id is not None:
        staff_user.slack_user_id = body.slack_user_id or None
    if body.telegram_user_id is not None:
        staff_user.telegram_user_id = body.telegram_user_id or None
    if body.employee_id is not None:
        staff_user.employee_id = body.employee_id or None
    if body.manager_email is not None:
        mgr = db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == body.manager_email.lower().strip())
        ).scalar_one_or_none()
        staff_user.manager_id = mgr.id if mgr else None

    if body.assignments is not None:
        # Remove existing assignments
        existing = db.execute(
            select(UserDepartment).where(UserDepartment.user_id == staff_user.id)
        ).scalars().all()
        for e in existing:
            db.delete(e)

        # Add new assignments
        tenant = get_primary_tenant(db)
        for a in body.assignments:
            dept = db.execute(
                select(Department).where(Department.tenant_id == tenant.id, Department.name == a.department)
            ).scalar_one_or_none()
            if dept:
                ud = UserDepartment(user_id=staff_user.id, department_id=dept.id, title=a.title)
                db.add(ud)
            else:
                logger.warning("Unknown department '%s' in update for staff %s", a.department, staff_user.email)

        db.add(staff_user)
    db.commit()
    db.refresh(staff_user)

    # Sync to brain
    from brain_sync import sync_staff_to_brain
    sync_staff_to_brain(staff_user, db)

    return {"ok": True, "user": _staff_response(staff_user, db)}


@router.delete("/{staff_id}")
async def delete_staff(
    staff_id: int,
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Remove a staff member's department assignments (soft-unlink)."""
    tenant = get_primary_tenant(db)
    staff_user = db.get(User, staff_id)
    if staff_user is None or staff_user.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Remove all department assignments (cascading)
    existing = db.execute(
        select(UserDepartment).where(UserDepartment.user_id == staff_user.id)
    ).scalars().all()
    for e in existing:
        db.delete(e)
    db.commit()
    return {"ok": True, "message": f"Removed {staff_user.name} from all departments"}


@router.post("/{staff_id}/reset-password")
async def reset_staff_password(
    staff_id: int,
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Generate a new temporary password for a staff member."""
    tenant = get_primary_tenant(db)
    staff_user = db.get(User, staff_id)
    if staff_user is None or staff_user.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Staff not found")

    temp_password = _generate_temp_password()
    staff_user.password_hash = hash_password(temp_password)
    staff_user.first_login = True
    staff_user.is_temporary_password = True
    db.add(staff_user)
    db.commit()

    return {
        "ok": True,
        "temporary_password": temp_password,
        "message": "Show this password to the user once. It will not be shown again.",
    }


@router.post("/import-csv")
async def import_staff_csv(
    file: UploadFile = File(...),
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Import staff from CSV. Creates portal accounts with temp passwords."""
    from brain_sync import sync_staff_to_brain

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    updated = 0
    skipped = 0
    errors: List[str] = []
    temp_passwords: Dict[str, str] = {}
    tenant = get_primary_tenant(db)

    for row_num, row in enumerate(reader, start=2):
        email = (row.get("email") or "").strip().lower()
        name = (row.get("name") or "").strip()
        dept_name = (row.get("department") or "").strip()

        if not email or not name:
            errors.append(f"Row {row_num}: missing email or name")
            skipped += 1
            continue

        dept = None
        if dept_name:
            dept = db.execute(
                select(Department).where(Department.tenant_id == tenant.id, Department.name == dept_name)
            ).scalar_one_or_none()
            if not dept:
                errors.append(f"Row {row_num}: unknown department '{dept_name}'")

        existing = db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == email)
        ).scalar_one_or_none()

        new_user = None
        if existing:
            existing.name = name
            existing.phone = row.get("phone") or existing.phone
            existing.slack_user_id = row.get("slack_id") or existing.slack_user_id
            existing.telegram_user_id = row.get("telegram_id") or existing.telegram_user_id
            existing.employee_id = row.get("employee_id") or existing.employee_id
            existing.source = "csv"
            db.add(existing)
            db.flush()
            updated += 1
        else:
            temp_pw = _generate_temp_password()
            new_user = User(
                tenant_id=tenant.id,
                email=email,
                name=name,
                role=(row.get("role") or "user").strip() or "user",
                password_hash=hash_password(temp_pw),
                first_login=True,
                is_temporary_password=True,
                phone=row.get("phone") or None,
                slack_user_id=row.get("slack_id") or None,
                telegram_user_id=row.get("telegram_id") or None,
                employee_id=row.get("employee_id") or None,
                source="csv",
                invited_by_id=user.id,
            )
            db.add(new_user)
            db.flush()
            temp_passwords[email] = temp_pw
            created += 1

        user_obj = existing or new_user
        if dept:
            existing_ud = db.execute(
                select(UserDepartment).where(
                    UserDepartment.user_id == user_obj.id,
                    UserDepartment.department_id == dept.id,
                )
            ).scalar_one_or_none()
            if not existing_ud:
                ud = UserDepartment(
                    user_id=user_obj.id,
                    department_id=dept.id,
                    title=row.get("title", "").strip() or "",
                )
                db.add(ud)

        sync_staff_to_brain(user_obj, db)

    db.commit()
    return {
        "ok": True,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "temporary_passwords": temp_passwords,
    }


@router.get("/directory")
async def staff_directory(
    q: str | None = None,
    department: str | None = None,
    role: str | None = None,
    source: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Searchable, filterable staff directory."""
    tenant = get_primary_tenant(db)
    query = select(User).where(User.tenant_id == tenant.id)

    if q:
        like = f"%{q}%"
        query = query.where(User.name.ilike(like) | User.email.ilike(like))
    if role:
        query = query.where(User.role == role)
    if source:
        query = query.where(User.source == source)

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    users = db.execute(query.order_by(User.name).offset(offset).limit(limit)).scalars().all()

    return {
        "staff": [_staff_response(u, db) for u in users],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/sync-briohr")
async def sync_briohr(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Trigger BrioHR employee sync."""
    from briohr_sync import sync_employees

    try:
        result = await sync_employees(db)
        return {"ok": True, **result}
    except Exception as exc:
        logger.exception("BrioHR sync failed")
        raise HTTPException(status_code=502, detail=str(exc))
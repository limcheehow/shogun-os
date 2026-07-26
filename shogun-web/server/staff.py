"""Staff management CRUD endpoints — admin/HR create and manage users."""
from __future__ import annotations

import logging
import secrets
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
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


class UpdateStaffPayload(BaseModel):
    name: str | None = None
    role: str | None = None
    assignments: List[AssignmentPayload] | None = None


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
    )
    db.add(new_user)
    db.flush()

    # Create department assignments
    for a in body.assignments:
        dept = db.execute(
            select(Department).where(Department.tenant_id == tenant.id, Department.name == a.department)
        ).scalar_one_or_none()
        if dept:
            ud = UserDepartment(user_id=new_user.id, department_id=dept.id, title=a.title)
            db.add(ud)

    db.commit()
    db.refresh(new_user)

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
    staff_user = db.get(User, staff_id)
    if staff_user is None:
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
    staff_user = db.get(User, staff_id)
    if staff_user is None:
        raise HTTPException(status_code=404, detail="Staff not found")

    if body.name is not None:
        staff_user.name = body.name.strip()
    if body.role is not None:
        if body.role in ("admin", "hr_manager") and user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admins can set this role")
        staff_user.role = body.role

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

    db.add(staff_user)
    db.commit()
    db.refresh(staff_user)
    return {"ok": True, "user": _staff_response(staff_user, db)}


@router.delete("/{staff_id}")
async def delete_staff(
    staff_id: int,
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Remove a staff member's department assignments (soft-unlink)."""
    staff_user = db.get(User, staff_id)
    if staff_user is None:
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
    staff_user = db.get(User, staff_id)
    if staff_user is None:
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
"""Auto-generate staff brain pages on every staff create/update."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from config import get_config
from models import User, UserDepartment

logger = logging.getLogger(__name__)

cfg = get_config()
STAFF_BRAIN_DIR = Path(cfg.brain_root).expanduser() / "shared" / "staff"


def _user_slug(user: User) -> str:
    """Generate a unique brain-page slug from user name + id."""
    name = user.name or user.email.split("@")[0]
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    base = slug.strip("-") or f"user-{user.id}"
    return f"{base}-{user.id}"


def sync_staff_to_brain(user: User, db: Session) -> Optional[Path]:
    """Write a staff brain page for the given user. Returns the path written."""
    assignments = (
        db.query(UserDepartment).filter(UserDepartment.user_id == user.id).all()
    )
    dept_names = ", ".join(a.department.name for a in assignments if a.department)
    titles = ", ".join(a.title for a in assignments if a.title)

    manager_name = ""
    if user.manager_id:
        mgr = db.get(User, user.manager_id)
        if mgr:
            manager_name = mgr.name

    slug = _user_slug(user)
    lines = [
        "---",
        f"type: staff",
        f"title: {user.name}",
        f"email: {user.email}",
        f"department: {dept_names}",
        f"role: {titles or user.role}",
        f"phone: {user.phone or ''}",
        f"slack_user_id: {user.slack_user_id or ''}",
        f"telegram_user_id: {user.telegram_user_id or ''}",
        f"employee_id: {user.employee_id or ''}",
        f"manager: {manager_name}",
        f"source: {user.source}",
        "---",
        "",
        f"# {user.name}",
        "",
        f"**Role:** {titles or user.role}",
        f"**Department:** {dept_names}",
        f"**Email:** {user.email}",
    ]

    if user.phone:
        lines.append(f"**Phone:** {user.phone}")
    if user.slack_user_id:
        lines.append(f"**Slack:** {user.slack_user_id}")
    if user.telegram_user_id:
        lines.append(f"**Telegram:** {user.telegram_user_id}")
    if user.employee_id:
        lines.append(f"**Employee ID:** {user.employee_id}")
    if manager_name:
        lines.append(f"**Manager:** {manager_name}")

    content = "\n".join(lines) + "\n"

    brain_path = STAFF_BRAIN_DIR / f"{slug}.md"
    brain_path.parent.mkdir(parents=True, exist_ok=True)
    brain_path.write_text(content, encoding="utf-8")
    logger.info("Wrote staff brain page: %s", brain_path)
    return brain_path
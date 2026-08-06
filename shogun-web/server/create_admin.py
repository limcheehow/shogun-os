"""Utility script to create or reset an admin user for Shogun OS Web Portal."""

import argparse
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import hash_password
from database import get_primary_tenant, init_db, session_scope
from models import User
from sqlalchemy import select


def create_or_reset_admin(email: str, password: str, name: str = "Admin"):
    init_db()
    email_clean = email.lower().strip()
    with session_scope() as db:
        tenant = get_primary_tenant(db)
        user = db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == email_clean)
        ).scalar_one_or_none()

        pw_hash = hash_password(password)
        if user:
            user.password_hash = pw_hash
            user.first_login = False
            user.role = "admin"
            print(f"Updated existing admin user: {email_clean}")
        else:
            user = User(
                tenant_id=tenant.id,
                email=email_clean,
                name=name,
                role="admin",
                password_hash=pw_hash,
                first_login=False,
            )
            db.add(user)
            print(f"Created new admin user: {email_clean}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or reset Shogun OS Admin user")
    parser.add_argument("--email", default="admin@localhost", help="Admin email address")
    parser.add_argument("--password", default="admin123456", help="Admin password")
    parser.add_argument("--name", default="Admin", help="Admin display name")
    args = parser.parse_args()

    create_or_reset_admin(args.email, args.password, args.name)

"""SQLAlchemy ORM models for the Shogun OS web portal."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all models."""


class Tenant(Base):
    """Per-installation tenant (usually one row on a customer machine)."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subdomain: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(256), nullable=False, default="Shogun OS")
    logo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    users: Mapped[List["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    departments: Mapped[List["Department"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    onboarding_states: Mapped[List["OnboardingState"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subdomain": self.subdomain,
            "company_name": self.company_name,
            "logo_url": self.logo_url,
            "timezone": self.timezone,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base):
    """Portal user belonging to a tenant."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    password_hash: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    oauth_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="admin")
    first_login: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_temporary_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invited_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    department_assignments: Mapped[List["UserDepartment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "name": self.name,
            "oauth_provider": self.oauth_provider,
            "role": self.role,
            "first_login": self.first_login,
            "is_temporary_password": self.is_temporary_password,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data["oauth_id"] = self.oauth_id
            data["has_password"] = bool(self.password_hash)
        return data


class UserDepartment(Base):
    """Many-to-many: users assigned to departments with a title."""

    __tablename__ = "user_departments"
    __table_args__ = (UniqueConstraint("user_id", "department_id", name="uq_user_dept"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="department_assignments")
    department: Mapped["Department"] = relationship()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else "",
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Department(Base):
    """Department profile activation + provider configuration."""

    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_departments_tenant_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="inactive")
    provider_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    gateway_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="departments")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "profile_name": self.profile_name,
            "status": self.status,
            "provider_config": self.provider_config or {},
            "gateway_port": self.gateway_port,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OnboardingState(Base):
    """Wizard progress for a tenant."""

    __tablename__ = "onboarding_states"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_onboarding_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="welcome")
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="onboarding_states")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "current_step": self.current_step,
            "data": self.data or {},
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed": self.completed_at is not None,
        }


class Session(Base):
    """Optional durable session audit trail (auth tokens themselves are HMAC-signed)."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="sessions")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

"""Database engine, session factory, and initialization for Shogun web portal."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterator, Optional

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config import DEFAULT_DEPARTMENTS, SHOGUN_HOME, get_config
from models import Base, Department, OnboardingState, Tenant

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_url() -> str:
    """Return the SQLAlchemy SQLite URL for this tenant."""
    cfg = get_config()
    db_path = Path(cfg.db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def get_engine(echo: bool = False) -> Engine:
    """Return (and lazily create) the shared SQLAlchemy engine."""
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            echo=echo,
        )
        if url.startswith("sqlite"):
            event.listen(_engine, "connect", _set_sqlite_pragma)
        logger.info("Database engine created: %s", url)
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the sessionmaker bound to the shared engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for scripts / startup hooks."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_tenant(db: Session) -> Tenant:
    """Create the default tenant row from config if missing."""
    cfg = get_config()
    tenant = db.execute(
        select(Tenant).where(Tenant.subdomain == cfg.subdomain)
    ).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(
            subdomain=cfg.subdomain,
            company_name=cfg.company_name,
            logo_url=cfg.logo_url or None,
            timezone=cfg.timezone,
            status=cfg.tenant_status,
        )
        db.add(tenant)
        db.flush()
        logger.info("Created tenant subdomain=%s id=%s", tenant.subdomain, tenant.id)
    else:
        # Keep config-driven fields in sync
        tenant.company_name = cfg.company_name
        tenant.logo_url = cfg.logo_url or None
        tenant.timezone = cfg.timezone
        tenant.status = cfg.tenant_status
    return tenant


def _ensure_departments(db: Session, tenant: Tenant) -> None:
    """Seed catalog departments as inactive if not present."""
    cfg = get_config()
    existing = {
        d.name: d
        for d in db.execute(
            select(Department).where(Department.tenant_id == tenant.id)
        ).scalars()
    }
    for spec in DEFAULT_DEPARTMENTS:
        name = spec["name"]
        if name in existing:
            continue
        port = cfg.gateway_port_base + int(spec.get("port_offset", 0))
        dept = Department(
            tenant_id=tenant.id,
            name=name,
            profile_name=spec["profile_name"],
            status="inactive",
            provider_config={},
            gateway_port=port,
        )
        db.add(dept)
        logger.info("Seeded department %s (port %s)", name, port)


def _ensure_onboarding(db: Session, tenant: Tenant) -> None:
    state = db.execute(
        select(OnboardingState).where(OnboardingState.tenant_id == tenant.id)
    ).scalar_one_or_none()
    if state is None:
        db.add(
            OnboardingState(
                tenant_id=tenant.id,
                current_step="welcome",
                data={},
                completed_at=None,
            )
        )


def init_db() -> None:
    """Create tables and seed tenant / department catalog."""
    SHOGUN_HOME.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    with session_scope() as db:
        tenant = _ensure_tenant(db)
        _ensure_departments(db, tenant)
        _ensure_onboarding(db, tenant)
    logger.info("Database initialized at %s", get_config().db_path)


def get_primary_tenant(db: Session) -> Tenant:
    """Return the primary (config subdomain) tenant or raise."""
    cfg = get_config()
    tenant = db.execute(
        select(Tenant).where(Tenant.subdomain == cfg.subdomain)
    ).scalar_one_or_none()
    if tenant is None:
        tenant = _ensure_tenant(db)
        db.flush()
    return tenant

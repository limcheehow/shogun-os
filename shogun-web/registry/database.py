"""SQLite persistence for the Shogun central registry."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from models import Tenant, TenantStatus, Tunnel, TunnelStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(value: Optional[str]) -> datetime:
    if not value:
        return _utcnow()
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Database:
    """Thread-safe thin wrapper around sqlite3."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.RLock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        with self._lock:
            conn = self._connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    subdomain TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'online',
                    last_seen TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    weight INTEGER NOT NULL DEFAULT 100,
                    instance_id TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_subdomain_instance
                    ON tenants(subdomain, COALESCE(instance_id, ''));

                CREATE INDEX IF NOT EXISTS idx_tenants_subdomain
                    ON tenants(subdomain);

                CREATE INDEX IF NOT EXISTS idx_tenants_status
                    ON tenants(status);

                CREATE TABLE IF NOT EXISTS tunnels (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    cloudflare_tunnel_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    dns_record_id TEXT,
                    tunnel_token TEXT,
                    name TEXT,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tunnels_tenant
                    ON tunnels(tenant_id);

                -- Public install bootstrap tickets (seamless customer install)
                CREATE TABLE IF NOT EXISTS install_tickets (
                    token TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    client_ip TEXT,
                    email TEXT,
                    redeemed_at TEXT,
                    tenant_id TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_install_tickets_ip_created
                    ON install_tickets(client_ip, created_at);
                CREATE INDEX IF NOT EXISTS idx_install_tickets_expires
                    ON install_tickets(expires_at);
                """
            )

    # ------------------------------------------------------------------
    # Tenants
    # ------------------------------------------------------------------

    def _row_to_tenant(self, row: sqlite3.Row) -> Tenant:
        meta_raw = row["metadata"] or "{}"
        try:
            meta = json.loads(meta_raw)
        except json.JSONDecodeError:
            meta = {}
        return Tenant(
            id=row["id"],
            subdomain=row["subdomain"],
            host=row["host"],
            port=int(row["port"]),
            status=TenantStatus(row["status"]),
            last_seen=_parse_dt(row["last_seen"]),
            created_at=_parse_dt(row["created_at"]),
            weight=int(row["weight"] or 100),
            instance_id=row["instance_id"],
            metadata=meta if isinstance(meta, dict) else {},
        )

    def create_tenant(
        self,
        *,
        subdomain: str,
        host: str,
        port: int,
        tenant_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        weight: int = 100,
        metadata: Optional[dict[str, Any]] = None,
        status: TenantStatus = TenantStatus.ONLINE,
    ) -> Tenant:
        tid = tenant_id or str(uuid.uuid4())
        now = _utcnow()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO tenants (
                    id, subdomain, host, port, status, last_seen, created_at,
                    weight, instance_id, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tid,
                    subdomain,
                    host,
                    port,
                    status.value,
                    _iso(now),
                    _iso(now),
                    weight,
                    instance_id,
                    json.dumps(metadata or {}),
                ),
            )
        return Tenant(
            id=tid,
            subdomain=subdomain,
            host=host,
            port=port,
            status=status,
            last_seen=now,
            created_at=now,
            weight=weight,
            instance_id=instance_id,
            metadata=metadata or {},
        )

    def upsert_tenant_instance(
        self,
        *,
        subdomain: str,
        host: str,
        port: int,
        tenant_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        weight: int = 100,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Tenant:
        """Insert or update a backend instance for a subdomain."""
        existing: Optional[Tenant] = None
        if tenant_id:
            existing = self.get_tenant(tenant_id)
        if existing is None and instance_id:
            existing = self.get_tenant_by_subdomain_instance(subdomain, instance_id)
        if existing is None and instance_id is None:
            # Single-instance tenants: update the primary row for subdomain
            rows = self.list_tenants_by_subdomain(subdomain)
            if len(rows) == 1 and rows[0].instance_id is None:
                existing = rows[0]

        if existing:
            return self.update_tenant(
                existing.id,
                host=host,
                port=port,
                status=TenantStatus.ONLINE,
                weight=weight,
                metadata=metadata,
                touch_last_seen=True,
                instance_id=instance_id if instance_id is not None else existing.instance_id,
            )

        return self.create_tenant(
            subdomain=subdomain,
            host=host,
            port=port,
            tenant_id=tenant_id,
            instance_id=instance_id,
            weight=weight,
            metadata=metadata,
        )

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM tenants WHERE id = ?", (tenant_id,)
            ).fetchone()
        return self._row_to_tenant(row) if row else None

    def get_tenant_by_subdomain_instance(
        self, subdomain: str, instance_id: Optional[str]
    ) -> Optional[Tenant]:
        with self.connection() as conn:
            if instance_id is None:
                row = conn.execute(
                    """
                    SELECT * FROM tenants
                    WHERE subdomain = ? AND instance_id IS NULL
                    LIMIT 1
                    """,
                    (subdomain,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM tenants
                    WHERE subdomain = ? AND instance_id = ?
                    LIMIT 1
                    """,
                    (subdomain, instance_id),
                ).fetchone()
        return self._row_to_tenant(row) if row else None

    def list_tenants_by_subdomain(self, subdomain: str) -> list[Tenant]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tenants WHERE subdomain = ? ORDER BY created_at ASC",
                (subdomain,),
            ).fetchall()
        return [self._row_to_tenant(r) for r in rows]

    def list_online_by_subdomain(self, subdomain: str) -> list[Tenant]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tenants
                WHERE subdomain = ? AND status = ?
                ORDER BY weight DESC, last_seen DESC
                """,
                (subdomain, TenantStatus.ONLINE.value),
            ).fetchall()
        return [self._row_to_tenant(r) for r in rows]

    def subdomain_exists(self, subdomain: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM tenants WHERE subdomain = ? LIMIT 1",
                (subdomain,),
            ).fetchone()
        return row is not None

    def list_tenants(
        self, *, status: Optional[TenantStatus] = None
    ) -> list[Tenant]:
        with self.connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM tenants WHERE status = ? ORDER BY created_at DESC",
                    (status.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tenants ORDER BY created_at DESC"
                ).fetchall()
        return [self._row_to_tenant(r) for r in rows]

    def update_tenant(
        self,
        tenant_id: str,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        status: Optional[TenantStatus] = None,
        weight: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        instance_id: Optional[str] = None,
        touch_last_seen: bool = False,
    ) -> Tenant:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"tenant not found: {tenant_id}")

        new_host = host if host is not None else tenant.host
        new_port = port if port is not None else tenant.port
        new_status = status if status is not None else tenant.status
        new_weight = weight if weight is not None else tenant.weight
        new_meta = metadata if metadata is not None else tenant.metadata
        new_instance = (
            instance_id if instance_id is not None else tenant.instance_id
        )
        new_last = _utcnow() if touch_last_seen else tenant.last_seen

        with self.connection() as conn:
            conn.execute(
                """
                UPDATE tenants SET
                    host = ?, port = ?, status = ?, weight = ?,
                    instance_id = ?, metadata = ?, last_seen = ?
                WHERE id = ?
                """,
                (
                    new_host,
                    new_port,
                    new_status.value,
                    new_weight,
                    new_instance,
                    json.dumps(new_meta),
                    _iso(new_last),
                    tenant_id,
                ),
            )
        updated = self.get_tenant(tenant_id)
        assert updated is not None
        return updated

    def heartbeat(
        self,
        tenant_id: str,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        status: TenantStatus = TenantStatus.ONLINE,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Tenant:
        return self.update_tenant(
            tenant_id,
            host=host,
            port=port,
            status=status,
            metadata=metadata,
            touch_last_seen=True,
        )

    def delete_tenant(self, tenant_id: str) -> bool:
        with self.connection() as conn:
            cur = conn.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
            return cur.rowcount > 0

    def delete_tenants_by_subdomain(self, subdomain: str) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM tenants WHERE subdomain = ?", (subdomain,)
            )
            return cur.rowcount

    def mark_stale_offline(self, stale_seconds: int) -> int:
        """Mark tenants without recent heartbeat as offline."""
        cutoff = _utcnow().timestamp() - stale_seconds
        updated = 0
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT id, last_seen, status FROM tenants WHERE status = ?",
                (TenantStatus.ONLINE.value,),
            ).fetchall()
            for row in rows:
                last = _parse_dt(row["last_seen"]).timestamp()
                if last < cutoff:
                    conn.execute(
                        "UPDATE tenants SET status = ? WHERE id = ?",
                        (TenantStatus.OFFLINE.value, row["id"]),
                    )
                    updated += 1
        return updated

    def set_status(self, tenant_id: str, status: TenantStatus) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                (status.value, tenant_id),
            )

    def counts(self) -> tuple[int, int]:
        with self.connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM tenants").fetchone()[
                "c"
            ]
            online = conn.execute(
                "SELECT COUNT(*) AS c FROM tenants WHERE status = ?",
                (TenantStatus.ONLINE.value,),
            ).fetchone()["c"]
        return int(online), int(total)

    # ------------------------------------------------------------------
    # Tunnels
    # ------------------------------------------------------------------

    def _row_to_tunnel(self, row: sqlite3.Row) -> Tunnel:
        return Tunnel(
            id=row["id"],
            tenant_id=row["tenant_id"],
            cloudflare_tunnel_id=row["cloudflare_tunnel_id"],
            status=TunnelStatus(row["status"]),
            created_at=_parse_dt(row["created_at"]),
            dns_record_id=row["dns_record_id"],
            tunnel_token=row["tunnel_token"],
            name=row["name"],
        )

    def create_tunnel(
        self,
        *,
        tenant_id: str,
        cloudflare_tunnel_id: str,
        status: TunnelStatus = TunnelStatus.PENDING,
        dns_record_id: Optional[str] = None,
        tunnel_token: Optional[str] = None,
        name: Optional[str] = None,
        tunnel_id: Optional[str] = None,
    ) -> Tunnel:
        tid = tunnel_id or str(uuid.uuid4())
        now = _utcnow()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO tunnels (
                    id, tenant_id, cloudflare_tunnel_id, status, created_at,
                    dns_record_id, tunnel_token, name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tid,
                    tenant_id,
                    cloudflare_tunnel_id,
                    status.value,
                    _iso(now),
                    dns_record_id,
                    tunnel_token,
                    name,
                ),
            )
        return Tunnel(
            id=tid,
            tenant_id=tenant_id,
            cloudflare_tunnel_id=cloudflare_tunnel_id,
            status=status,
            created_at=now,
            dns_record_id=dns_record_id,
            tunnel_token=tunnel_token,
            name=name,
        )

    def get_tunnel(self, tunnel_id: str) -> Optional[Tunnel]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM tunnels WHERE id = ?", (tunnel_id,)
            ).fetchone()
        return self._row_to_tunnel(row) if row else None

    def list_tunnels_for_tenant(self, tenant_id: str) -> list[Tunnel]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tunnels WHERE tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
        return [self._row_to_tunnel(r) for r in rows]

    def list_tunnels(self) -> list[Tunnel]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tunnels ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_tunnel(r) for r in rows]

    def update_tunnel_status(
        self,
        tunnel_id: str,
        status: TunnelStatus,
        *,
        dns_record_id: Optional[str] = None,
    ) -> None:
        with self.connection() as conn:
            if dns_record_id is not None:
                conn.execute(
                    "UPDATE tunnels SET status = ?, dns_record_id = ? WHERE id = ?",
                    (status.value, dns_record_id, tunnel_id),
                )
            else:
                conn.execute(
                    "UPDATE tunnels SET status = ? WHERE id = ?",
                    (status.value, tunnel_id),
                )

    def delete_tunnel(self, tunnel_id: str) -> bool:
        with self.connection() as conn:
            cur = conn.execute("DELETE FROM tunnels WHERE id = ?", (tunnel_id,))
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Install tickets (public bootstrap)
    # ------------------------------------------------------------------

    def count_recent_tickets(self, client_ip: str, since_iso: str) -> int:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c FROM install_tickets
                WHERE client_ip = ? AND created_at >= ?
                """,
                (client_ip or "", since_iso),
            ).fetchone()
        return int(row["c"] if row else 0)

    def create_install_ticket(
        self,
        *,
        token: str,
        expires_at: datetime,
        client_ip: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        now = _utcnow()
        meta = json.dumps(metadata or {})
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO install_tickets
                    (token, created_at, expires_at, client_ip, email, redeemed_at, tenant_id, metadata)
                VALUES (?, ?, ?, ?, ?, NULL, NULL, ?)
                """,
                (
                    token,
                    _iso(now),
                    _iso(expires_at),
                    client_ip or "",
                    email,
                    meta,
                ),
            )
        return {
            "token": token,
            "created_at": now,
            "expires_at": expires_at,
            "client_ip": client_ip,
            "email": email,
        }

    def get_install_ticket(self, token: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM install_tickets WHERE token = ?",
                (token,),
            ).fetchone()
        if not row:
            return None
        try:
            meta = json.loads(row["metadata"] or "{}")
        except json.JSONDecodeError:
            meta = {}
        return {
            "token": row["token"],
            "created_at": _parse_dt(row["created_at"]),
            "expires_at": _parse_dt(row["expires_at"]),
            "client_ip": row["client_ip"],
            "email": row["email"],
            "redeemed_at": _parse_dt(row["redeemed_at"]) if row["redeemed_at"] else None,
            "tenant_id": row["tenant_id"],
            "metadata": meta,
        }

    def redeem_install_ticket(self, token: str, tenant_id: str) -> bool:
        """Mark ticket redeemed. Returns False if missing/expired/already used."""
        now = _utcnow()
        with self.connection() as conn:
            row = conn.execute(
                "SELECT expires_at, redeemed_at FROM install_tickets WHERE token = ?",
                (token,),
            ).fetchone()
            if not row:
                return False
            if row["redeemed_at"]:
                return False
            exp = _parse_dt(row["expires_at"])
            if exp < now:
                return False
            cur = conn.execute(
                """
                UPDATE install_tickets
                SET redeemed_at = ?, tenant_id = ?
                WHERE token = ? AND redeemed_at IS NULL
                """,
                (_iso(now), tenant_id, token),
            )
            return cur.rowcount > 0

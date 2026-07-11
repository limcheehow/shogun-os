---
name: session-db-postgres
id: session-db-postgres
category: infra
setup_time: 20
cost: $0
depends_on: [postgresql]
---

# Session DB — Shared Postgres

Migrate from per-profile SQLite to shared Postgres for multi-profile deployments. Eliminates SQLite lock contention.

## Setup

1. Install PostgreSQL:
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl enable --now postgresql
```

2. Create the database and user:
```bash
sudo -u postgres psql -c "CREATE USER hermes WITH PASSWORD 'your-password';"
sudo -u postgres psql -c "CREATE DATABASE hermes_sessions OWNER hermes;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hermes_sessions TO hermes;"
```

3. Configure the session-postgres plugin in each profile's `config.yaml`:
```yaml
plugins:
  session-postgres:
    dsn: "postgresql://hermes:your-password@localhost:5432/hermes_sessions"
    pool_size: 5
```

4. Run the health check:
```bash
python3 scripts/session-db-health-check.sh
```

## Cron Jobs

| Job | Schedule | Script | Purpose |
|-----|----------|--------|---------|
| Session DB Health | Daily 7AM | `session-db-health-check.sh` | Postgres connection + table integrity |

## Config

```yaml
# Per-profile config.yaml
plugins:
  session-postgres:
    dsn: "postgresql://hermes:${DB_PASSWORD}@localhost:5432/hermes_sessions"
    pool_size: 5
```

## Key Benefits

| Aspect | SQLite (per-profile) | Postgres (shared) |
|--------|---------------------|-------------------|
| Lock contention | WAL mode helps but can still block | MVCC — no reader/writer blocking |
| Multi-profile | Separate DB per profile | One DB, all profiles |
| Backup | Copy .db files | `pg_dump` — consistent snapshots |
| Concurrent writes | Limited | Full concurrent write support |
| Scale | ~300MB per profile | Unlimited |

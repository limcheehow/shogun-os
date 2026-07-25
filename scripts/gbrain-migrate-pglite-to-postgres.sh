#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Shogun OS — GBrain PGLite → Postgres Migration Script
# ──────────────────────────────────────────────────────────────────────────
# Migrates gbrain from PGLite (local SQLite) to PostgreSQL/Supabase.
# Creates a timestamped backup before migration, verifies Postgres
# connectivity, ensures pgvector extension, and runs health checks
# on success.
#
# Usage:
#   ./scripts/gbrain-migrate-pglite-to-postgres.sh
#
# Environment variables (all optional):
#   GBRAIN_DB_HOST   Postgres host (default: 127.0.0.1)
#   GBRAIN_DB_PORT   Postgres port (default: 5432)
#   GBRAIN_DB_USER   Postgres user (default: gbrain)
#   GBRAIN_DB_NAME   Postgres database (default: gbrain)
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

VERSION="1.0.0"

# ── Default configuration ──────────────────────────────────────────────
GBRAIN_DB_HOST="${GBRAIN_DB_HOST:-127.0.0.1}"
GBRAIN_DB_PORT="${GBRAIN_DB_PORT:-5432}"
GBRAIN_DB_USER="${GBRAIN_DB_USER:-gbrain}"
GBRAIN_DB_NAME="${GBRAIN_DB_NAME:-gbrain}"

# Password for PostgreSQL authentication.
# Set GBRAIN_DB_PASSWORD env var before running (default: 'gbrain').
# This is exported as PGPASSWORD so psql/pg_isready use it automatically.
export PGPASSWORD="${GBRAIN_DB_PASSWORD:-gbrain}"

POSTGRES_URL="postgresql://${GBRAIN_DB_USER}@${GBRAIN_DB_HOST}:${GBRAIN_DB_PORT}/${GBRAIN_DB_NAME}"

GBRAIN_BINARY=""
BACKUP_DIR="${HOME}/backups/gbrain-pre-migration"

# ── Color helpers (matching init-gbrain.sh style) ──────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()    { echo -e "  ${GREEN}✅${NC} $1"; }
info()  { echo -e "  ${CYAN}💡${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠️${NC} $1"; }
err()   { echo -e "  ${RED}❌${NC} $1"; }

# ── Helper functions ───────────────────────────────────────────────────

resolve_gbrain() {
  if command -v gbrain &>/dev/null; then
    GBRAIN_BINARY="$(command -v gbrain)"
    info "Found gbrain in PATH: ${GBRAIN_BINARY}"
  elif [ -x "${HOME}/.bun/bin/gbrain" ]; then
    GBRAIN_BINARY="${HOME}/.bun/bin/gbrain"
    info "Found gbrain in ~/.bun/bin: ${GBRAIN_BINARY}"
  else
    err "gbrain binary not found in PATH or ~/.bun/bin/gbrain"
    err "Install gbrain first: curl -fsSL https://bun.sh/install | bash && bun install -g gbrain"
    exit 1
  fi
}

check_engine() {
  local engine
  info "Checking current gbrain engine..."
  engine=$("${GBRAIN_BINARY}" config get engine 2>&1) || true

  if [ "${engine}" = "postgres" ]; then
    ok "Engine is already 'postgres' — nothing to do."
    exit 0
  fi

  info "Current engine: '${engine}' — proceeding with migration from PGLite to PostgreSQL."
}

verify_postgres_reachable() {
  info "Verifying Postgres is reachable at ${GBRAIN_DB_HOST}:${GBRAIN_DB_PORT}..."
  if command -v pg_isready &>/dev/null; then
    if pg_isready -h "${GBRAIN_DB_HOST}" -p "${GBRAIN_DB_PORT}" -q; then
      ok "Postgres is reachable at ${GBRAIN_DB_HOST}:${GBRAIN_DB_PORT}"
    else
      err "Postgres is NOT reachable at ${GBRAIN_DB_HOST}:${GBRAIN_DB_PORT}"
      err "Ensure PostgreSQL is running and accepting connections."
      err "  sudo systemctl start postgresql"
      err "  sudo pg_ctlcluster 16 main start"
      exit 1
    fi
  else
    err "pg_isready not found in PATH. Install PostgreSQL client tools."
    err "  sudo apt-get install -y postgresql-client"
    exit 1
  fi
}

backup_gbrain() {
  local timestamp
  timestamp="$(date +%Y%m%d_%H%M%S)"
  local backup_path="${BACKUP_DIR}/gbrain_${timestamp}"

  info "Creating timestamped backup of ~/.gbrain to ${backup_path}..."
  mkdir -p "${BACKUP_DIR}"

  if [ -d "${HOME}/.gbrain" ]; then
    cp -a "${HOME}/.gbrain" "${backup_path}"
    ok "Backup created at ${backup_path}"
  else
    warn "~/.gbrain directory does not exist — skipping backup."
  fi
}

ensure_pgvector() {
  info "Ensuring pgvector extension exists on target database..."
  if command -v psql &>/dev/null; then
    if psql -h "${GBRAIN_DB_HOST}" -p "${GBRAIN_DB_PORT}" -U "${GBRAIN_DB_USER}" -d "${GBRAIN_DB_NAME}" \
      -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1; then
      ok "pgvector extension is present on ${GBRAIN_DB_NAME}"
    else
      err "Failed to create pgvector extension. Is pgvector installed on the server?"
      err "  sudo apt-get install -y postgresql-16-pgvector"
      err "  or: CREATE EXTENSION vector; (via superuser)"
      exit 1
    fi
  else
    warn "psql not in PATH — skipping pgvector check. Ensure pgvector is installed manually."
  fi
}

run_migration() {
  info "Running migration: gbrain migrate --to supabase --url ${POSTGRES_URL} --force"
  if "${GBRAIN_BINARY}" migrate --to supabase --url "${POSTGRES_URL}" --force; then
    ok "Migration completed successfully."
  else
    err "Migration FAILED."
    print_restore_instructions
    exit 1
  fi
}

verify_migration() {
  info "Verifying migration — running gbrain doctor..."
  if "${GBRAIN_BINARY}" doctor; then
    ok "gbrain doctor — all checks passed."
  else
    warn "gbrain doctor reported issues (may be benign post-migration)."
  fi

  info "Running gbrain stats..."
  "${GBRAIN_BINARY}" stats
  ok "gbrain stats retrieved."
}

print_restore_instructions() {
  echo ""
  err "═══ RESTORE INSTRUCTIONS ═══"
  err "A backup was created at: ${BACKUP_DIR}"
  err ""
  err "To restore from backup:"
  err "  1. Stop any running gbrain services"
  err "  2. Restore backup:  rm -rf ~/.gbrain && cp -a ${BACKUP_DIR}/gbrain_* ~/.gbrain"
  err "  3. Reset engine back to PGLite:"
  err "       gbrain config set engine pglite"
  err "  4. Verify: gbrain doctor && gbrain stats"
  err "═══════════════════════════════"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────────────

echo ""
echo -e "  ${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "  ${CYAN}   GBrain PGLite → Postgres Migration Script v${VERSION}${NC}"
echo -e "  ${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

resolve_gbrain
echo ""

check_engine
echo ""

verify_postgres_reachable
echo ""

backup_gbrain
echo ""

ensure_pgvector
echo ""

run_migration
echo ""

verify_migration
echo ""

ok "Migration complete! Engine is now PostgreSQL."
info "Target database: ${POSTGRES_URL}"
info "Backup location: ${BACKUP_DIR}"
echo ""
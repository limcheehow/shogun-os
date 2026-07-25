#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# GBrain pg_dump Backup Script
# =============================================================================
# Creates compressed PostgreSQL dumps of the gbrain database with
# configurable retention and logging.
#
# Configuration (via environment variables):
#   GBRAIN_BACKUP_DIR       - Backup output directory (default: ~/backups/gbrain)
#   GBRAIN_DB_NAME          - Database name (default: gbrain)
#   GBRAIN_DB_USER          - Database user (default: gbrain)
#   GBRAIN_DB_HOST          - Database host (default: 127.0.0.1)
#   GBRAIN_DB_PORT          - Database port (default: 5432)
#   GBRAIN_BACKUP_RETENTION - Days to keep backups (default: 7)
# =============================================================================

# --- Configuration with defaults ---
BACKUP_DIR="${GBRAIN_BACKUP_DIR:-$HOME/backups/gbrain}"
DB_NAME="${GBRAIN_DB_NAME:-gbrain}"
DB_USER="${GBRAIN_DB_USER:-gbrain}"
DB_HOST="${GBRAIN_DB_HOST:-127.0.0.1}"
DB_PORT="${GBRAIN_DB_PORT:-5432}"
RETENTION_DAYS="${GBRAIN_BACKUP_RETENTION:-7}"

# --- Derived values ---
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="${BACKUP_DIR}/gbrain_${TIMESTAMP}.sql.gz"
LOG_DIR="$HOME/.gbrain/logs"
LOG_FILE="${LOG_DIR}/backup-$(date '+%Y%m%d').log"

# --- Ensure directories exist ---
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

# --- Log helper ---
log() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${message}" >> "$LOG_FILE"
}

# --- Start ---
log "INFO" "=== GBrain Backup Started ==="
log "INFO" "Database: ${DB_NAME} on ${DB_HOST}:${DB_PORT} (user: ${DB_USER})"
log "INFO" "Output:   ${BACKUP_FILE}"
log "INFO" "Retention: ${RETENTION_DAYS} days"

# --- Run pg_dump ---
log "INFO" "Running pg_dump ..."
if pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-password \
    --clean \
    --if-exists \
    2>> "$LOG_FILE" \
    | gzip > "$BACKUP_FILE"
then
    BACKUP_SIZE=$(stat --format=%s "$BACKUP_FILE" 2>/dev/null || echo 0)
    log "INFO" "Backup completed successfully (${BACKUP_SIZE} bytes)"
else
    log "ERROR" "pg_dump failed — backup NOT created"
    exit 1
fi

# --- Prune old backups ---
log "INFO" "Pruning backups older than ${RETENTION_DAYS} days in ${BACKUP_DIR} ..."
# Remove files matching the backup pattern that are older than RETENTION_DAYS
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'gbrain_*.sql.gz' -mtime "+${RETENTION_DAYS}" -print -delete 2>> "$LOG_FILE" | \
while read -r pruned_file; do
    log "INFO" "Pruned old backup: ${pruned_file}"
done

PRUNED_COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'gbrain_*.sql.gz' | wc -l)
log "INFO" "Retained backups in ${BACKUP_DIR}: ${PRUNED_COUNT} file(s)"

# =============================================================================
# TODO: Optional git push to remote backup repository
# =============================================================================
# Uncomment and configure the section below to push backups to a remote git repo.
#
# Example:
#   BACKUP_REPO="$HOME/backups/gbrain-git"
#   if [ -d "$BACKUP_REPO/.git" ]; then
#       cp "$BACKUP_FILE" "$BACKUP_REPO/"
#       cd "$BACKUP_REPO"
#       git add "gbrain_${TIMESTAMP}.sql.gz"
#       git commit -m "gbrain backup ${TIMESTAMP}"
#       git push origin main
#   fi
#
# =============================================================================

log "INFO" "=== GBrain Backup Completed Successfully ==="
#!/usr/bin/env bash
set -euo pipefail

# Hermes Database Backup Script
# Creates timestamped snapshots, prunes old ones, optionally syncs to cloud storage
#
# Config (edit these or set via environment variables):
#   BACKUP_DIR   — where local snapshots are stored (default: $HOME/.hermes/state-snapshots)
#   RETENTION    — keep last N backups (default: 10)
#   GDRIVE_REMOTE — rclone remote path (optional — set to empty to skip cloud sync)
#   CLOUD_REMOTE — alternative cloud sync target (rclone-style)
#
# Environment variables override defaults:
#   HERMES_BACKUP_DIR
#   HERMES_BACKUP_RETENTION
#   HERMES_CLOUD_REMOTE

BACKUP_DIR="${HERMES_BACKUP_DIR:-$HOME/.hermes/state-snapshots}"
RETENTION="${HERMES_BACKUP_RETENTION:-10}"
# Set this to an rclone remote path (e.g., "gdrive:MyBackups") to enable cloud sync
# Leave empty to skip cloud sync entirely
CLOUD_REMOTE="${HERMES_CLOUD_REMOTE:-}"

LOCKFILE="/tmp/hermes-backup.lock"
exec 200>"$LOCKFILE"
flock -n 200 || exit 0  # skip if another backup is running

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SNAPSHOT_DIR="$BACKUP_DIR/$TIMESTAMP"

# 1. Create snapshot directory
mkdir -p "$SNAPSHOT_DIR"

# 2. Copy essential files
cp -a "$HOME/.hermes/config.yaml" "$SNAPSHOT_DIR/config.yaml" 2>/dev/null || true
cp -a "$HOME/.hermes/cron.db" "$SNAPSHOT_DIR/cron.db" 2>/dev/null || true
cp -a "$HOME/.hermes/kanban.db" "$SNAPSHOT_DIR/kanban.db" 2>/dev/null || true

# 3. Session data (Postgres or SQLite)
#    Postgres backups are handled by pg_dump separately.
#    If using SQLite, uncomment below:
# cp -a "$HOME/.hermes/state.db" "$SNAPSHOT_DIR/state.db" 2>/dev/null || true

# 4. Write manifest
cat > "$SNAPSHOT_DIR/manifest.json" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "files": {
    "cron.db": $(test -f "$SNAPSHOT_DIR/cron.db" && echo "true" || echo "false"),
    "kanban.db": $(test -f "$SNAPSHOT_DIR/kanban.db" && echo "true" || echo "false"),
    "config.yaml": $(test -f "$SNAPSHOT_DIR/config.yaml" && echo "true" || echo "false")
  }
}
EOF

# 5. Report size
SIZE=$(du -sh "$SNAPSHOT_DIR" | cut -f1)
echo "Backup created: $SNAPSHOT_DIR ($SIZE)"

# 6. Prune old backups
COUNT=$(ls -1 "$BACKUP_DIR" | grep -E '^[0-9]{8}-[0-9]{6}$' | sort | wc -l)
if [ "$COUNT" -gt "$RETENTION" ]; then
    TO_DELETE=$((COUNT - RETENTION))
    echo "Pruning $TO_DELETE old backup(s)..."
    ls -1 "$BACKUP_DIR" | grep -E '^[0-9]{8}-[0-9]{6}$' | sort | head -"$TO_DELETE" | while read -r dir; do
        rm -rf "$BACKUP_DIR/$dir"
        echo "  Removed: $dir"
    done
fi

# 7. Sync to cloud storage (optional)
if [ -n "$CLOUD_REMOTE" ]; then
    echo "Syncing to cloud storage ($CLOUD_REMOTE)..."
    if command -v rclone &>/dev/null; then
        rclone copy "$BACKUP_DIR" "$CLOUD_REMOTE" \
            --update --verbose --ignore-errors --transfers 2 \
            2>&1 | tail -5
        echo "Cloud sync done."
    else
        echo "⚠️ rclone not found — skipping cloud sync"
    fi
else
    echo "No cloud remote configured — backup is local only."
    echo "  Set HERMES_CLOUD_REMOTE env var (e.g. 'gdrive:MyBackups') to enable."
fi

echo "Backup complete."
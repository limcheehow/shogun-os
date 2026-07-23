# rclone Bisync: Cron Scheduling

Scheduling a two-way sync between local folders and Google Drive with Hermes cron.

## One-Shot Bisync (Dry Run Always First)

```bash
# First sync: --resync to establish baseline (forces full reconciliation)
rclone bisync ~/local-folder gdrive:remote-folder --resync

# Subsequent syncs: faster, incremental
rclone bisync ~/local-folder gdrive:remote-folder
```

Important flags:
- `--dry-run` — preview changes without executing
- `--resync` — full reconciliation (use on first run or after manual changes)
- `--conflict-resolve newer` — auto-resolve conflicts by modification time (default)
- `--create-empty-src-dirs` — mirror empty directories
- `--remove-empty-dirs` — clean up empty dirs on both sides
- `--verbose` — see every file action

## The Sync Script Pattern

Create a script at `~/.hermes/scripts/rclone-sync.sh`:

```bash
#!/bin/bash
set -e

RCLONE="$HOME/.local/bin/rclone"
SYNC_PAIRS=(
  "$HOME/brain:gdrive:brain-backup"
  "$HOME/Documents:gdrive:Documents"
)

for pair in "${SYNC_PAIRS[@]}"; do
  IFS=: read -r LOCAL REMOTE_DIR <<< "$pair"
  REMOTE="gdrive:$REMOTE_DIR"
  
  echo "$(date -Iseconds) Syncing $LOCAL ↔ $REMOTE"
  
  # Dry-run first to detect conflicts
  if ! DRY=$("$RCLONE" bisync "$LOCAL" "$REMOTE" --dry-run 2>&1); then
    echo "DRY-RUN FAILED: $DRY"
    continue
  fi
  
  if echo "$DRY" | grep -q "Bisync aborted"; then
    echo "CONFLICT DETECTED in $LOCAL ↔ $REMOTE — manual intervention needed"
    echo "$DRY"
    continue
  fi
  
  # Safe to run
  "$RCLONE" bisync "$LOCAL" "$REMOTE" --conflict-resolve newer
  echo "Done: $LOCAL ↔ $REMOTE"
done
```

## Cron Job via Hermes

```bash
hermes cron create "0 */6 * * *" \
  --script ~/.hermes/scripts/rclone-sync.sh \
  --name "rclone-drive-sync" \
  --prompt "Sync completed. Report the results."
```

Or using cronjob tool directly:
```
cronjob(action='create', schedule='0 */6 * * *', script='/home/your-company/.hermes/scripts/rclone-sync.sh', name='rclone-drive-sync')
```

## Conflict Resolution

rclone bisync detects these conflict types:
- Both sides modified since last sync → newer-wins (with `--conflict-resolve newer`)
- File deleted on both sides → both deleted
- File deleted on one side, modified on other → preserved

For safety, prefer `--dry-run` before every sync in the script. If conflicts are detected, the script logs them for manual review instead of silently resolving.

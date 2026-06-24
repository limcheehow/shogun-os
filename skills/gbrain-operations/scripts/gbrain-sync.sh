#!/usr/bin/bash
# gbrain-sync.sh — Incremental brain sync via gbrain CLI
# Designed for cron (no_agent mode) — silent on success, noisy on failure.
# Run every 15 minutes.

GBRAIN_DIR="$HOME/gbrain"
BRAIN_DIR="$HOME/brain"

cd "$GBRAIN_DIR" || { echo "ERROR: gbrain dir not found"; exit 1; }

# Step 1: Clear stale locks (older than 30 min)
CLEARED=$(/usr/bin/python3 -c "
import psycopg2, json
cfg = json.load(open('$HOME/.gbrain/config.json'))
conn = psycopg2.connect(cfg['database_url'], sslmode='require')
cur = conn.cursor()
cur.execute(\"DELETE FROM gbrain_cycle_locks WHERE ttl_expires_at < now() - interval '30 minutes'\")
n = cur.rowcount
conn.commit()
cur.close(); conn.close()
print(n)
" 2>/dev/null)

[ -n "$CLEARED" ] && [ "$CLEARED" -gt 0 ] && echo "Cleared $CLEARED stale lock(s)"

# Step 2: Run sync (skips if another sync is in progress)
OUTPUT=$(bun run src/cli.ts sync --repo "$BRAIN_DIR" --skip-failed 2>&1)
EXIT_CODE=$?

# Step 3: Report only meaningful events
if [ $EXIT_CODE -eq 0 ]; then
    IMPORTED=$(echo "$OUTPUT" | grep -oP 'imported=\K[0-9]+' | tail -1)
    if [ -n "$IMPORTED" ] && [ "$IMPORTED" -gt 0 ]; then
        echo "Sync complete: $IMPORTED new files imported"
    fi
else
    if echo "$OUTPUT" | grep -q "Another sync is in progress"; then
        : # Silent — previous sync still running, this is normal
    else
        echo "Sync failed (exit $EXIT_CODE):"
        echo "$OUTPUT" | tail -5
        exit $EXIT_CODE
    fi
fi

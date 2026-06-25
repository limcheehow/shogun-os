# gbrain-sync.sh — Incremental brain sync via gbrain CLI
# Designed for cron (no_agent mode) — silent on success, noisy on failure.
# Run every 15 minutes. Edit BRAIN_DIR and GBRAIN_CONFIG_DIR for your setup.

GBRAIN_CONFIG_DIR="${GBRAIN_CONFIG_DIR:-$HOME/.gbrain}"
BRAIN_DIR="${BRAIN_DIR:-$HOME/brain}"

cd "$BRAIN_DIR" || { echo "ERROR: brain dir not found at $BRAIN_DIR"; exit 1; }

# Step 1: Clear stale locks (older than 30 min) — only if config.json exists
if [ -f "$GBRAIN_CONFIG_DIR/config.json" ]; then
    CLEARED=$(/usr/bin/python3 -c "
import json, os
cfg_path = os.path.expanduser('$GBRAIN_CONFIG_DIR/config.json')
cfg = json.load(open(cfg_path))
db_url = cfg.get('database_url') or cfg.get('database') or ''
if not db_url:
    exit(0)
import psycopg2
conn = psycopg2.connect(db_url, sslmode='require')
cur = conn.cursor()
cur.execute(\"DELETE FROM gbrain_cycle_locks WHERE ttl_expires_at < now() - interval '30 minutes'\")
n = cur.rowcount
conn.commit()
cur.close(); conn.close()
print(n)
" 2>/dev/null)
    [ -n "$CLEARED" ] && [ "$CLEARED" -gt 0 ] && echo "Cleared $CLEARED stale lock(s)"
fi

# Step 2: Run sync
OUTPUT=$(gbrain sync 2>&1)
EXIT_CODE=$?

# Step 3: Report only meaningful events
if [ $EXIT_CODE -eq 0 ]; then
    echo "Sync complete: $(echo "$OUTPUT" | grep -oP 'imported=\K[0-9]+' | tail -1 || echo '0') files"
else
    if echo "$OUTPUT" | grep -qi "sync is in progress\|lock conflict"; then
        : # Silent — previous sync still running, this is normal
    else
        echo "Sync failed (exit $EXIT_CODE):"
        echo "$OUTPUT" | tail -5
        exit $EXIT_CODE
    fi
fi

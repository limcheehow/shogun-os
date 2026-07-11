#!/usr/bin/env bash
# Daily session DB health check — checks PostgreSQL or SQLite (all profiles) + gateway processes.
# Supports both Postgres (shared DB via session-postgres plugin) and per-profile SQLite.
# Success: clean per-profile status. Failure: clear alert with fix instructions.
#
# CONFIG: Set DB_TYPE env var to "postgres" or "sqlite" (default: auto-detect).
# Set DB_NAME, DB_USER, PG_HOST for Postgres config.
# Override PROFILES list via PROFILES env var (space-separated).
set -euo pipefail

DB_TYPE="${DB_TYPE:-auto}"
DB_NAME="${DB_NAME:-hermes_sessions}"
DB_USER="${DB_USER:-hermes}"
PG_HOST="${PG_HOST:-localhost}"

# Default profiles — override with PROFILES env var
if [ -n "${PROFILES:-}" ]; then
    IFS=' ' read -ra PROFILES <<< "$PROFILES"
else
    PROFILES=(crm-manager hr-manager marketing-manager project-manager product-manager)
fi

ALL_OK=true

# ── Auto-detect DB type ──
if [ "$DB_TYPE" = "auto" ]; then
    if command -v psql &>/dev/null && psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT 1;" 2>/dev/null | grep -q "1"; then
        DB_TYPE="postgres"
    elif [ -f "$HOME/.hermes/sessions.db" ] || [ -f "$HOME/.hermes/state.db" ]; then
        DB_TYPE="sqlite"
    else
        echo "⚠️ Could not auto-detect database type."
        echo "   Set DB_TYPE=postgres or DB_TYPE=sqlite explicitly."
        ALL_OK=false
    fi
fi

# ── 1. Database connection check ──
check_postgres() {
    local check
    check=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT 1;" 2>&1 | tr -d '[:space:]')
    if [ "$check" != "1" ]; then
        echo "❌ [postgres] Cannot connect to $DB_NAME database."
        echo "   Fix: sudo systemctl restart postgresql"
        ALL_OK=false
        return 1
    fi

    # Table integrity
    local integ
    integ=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT count(*) FROM sessions; SELECT count(*) FROM messages;" 2>&1)
    if echo "$integ" | grep -q "ERROR"; then
        echo "❌ [postgres] Connected but queries fail: $integ"
        ALL_OK=false
        return 1
    fi

    local total_sessions total_msgs
    total_sessions=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT count(*) FROM sessions;" 2>/dev/null | tr -d '[:space:]')
    total_msgs=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT count(*) FROM messages;" 2>/dev/null | tr -d '[:space:]')
    echo "✅ [postgres] $DB_NAME healthy — $total_sessions sessions | $total_msgs messages."

    echo ""
    echo "  Sessions by source:"
    psql -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c \
        "SELECT source, count(*)::text, coalesce(sum(message_count),0)::text
         FROM sessions GROUP BY source ORDER BY count(*) DESC;" 2>/dev/null | \
        while IFS='|' read -r source sessions msgs; do
            [ -z "$source" ] && continue
            printf "    %-12s %5s sessions, %7s msgs\n" "$source" "$sessions" "$msgs"
        done
}

check_sqlite() {
    local db_path="$HOME/.hermes/sessions.db"
    if [ ! -f "$db_path" ]; then
        db_path="$HOME/.hermes/state.db"
    fi
    if [ ! -f "$db_path" ]; then
        echo "❌ [sqlite] No session database found."
        ALL_OK=false
        return 1
    fi

    if ! sqlite3 "$db_path" "SELECT 1;" 2>/dev/null | grep -q "1"; then
        echo "❌ [sqlite] Cannot query $db_path"
        ALL_OK=false
        return 1
    fi

    local total_sessions total_msgs
    total_sessions=$(sqlite3 "$db_path" "SELECT count(*) FROM sessions;" 2>/dev/null || echo "0")
    total_msgs=$(sqlite3 "$db_path" "SELECT count(*) FROM messages;" 2>/dev/null || echo "0")
    echo "✅ [sqlite] $(basename $db_path) healthy — $total_sessions sessions | $total_msgs messages."

    echo ""
    echo "  Sessions by source:"
    sqlite3 "$db_path" "SELECT source, count(*), coalesce(sum(message_count),0) FROM sessions GROUP BY source ORDER BY count(*) DESC;" 2>/dev/null | \
        while IFS='|' read -r source sessions msgs; do
            [ -z "$source" ] && continue
            printf "    %-12s %5s sessions, %7s msgs\n" "$source" "$sessions" "$msgs"
        done
}

if [ "$DB_TYPE" = "postgres" ]; then
    check_postgres
elif [ "$DB_TYPE" = "sqlite" ]; then
    check_sqlite
fi

# ── 2. Profile gateway process health ──
echo ""
echo "  Profile gateways:"

# Default gateway (systemd)
DEFAULT_STATUS=$(systemctl --user is-active hermes-gateway.service 2>/dev/null || echo "unknown")
if [ "$DEFAULT_STATUS" = "active" ]; then
    DEFAULT_PID=$(systemctl --user show hermes-gateway.service --property=MainPID 2>/dev/null | cut -d= -f2)
    echo "    ✅ [default] Gateway running — PID $DEFAULT_PID."
else
    echo "    ❌ [default] Gateway NOT running (status: $DEFAULT_STATUS)."
    echo "       Fix: systemctl --user start hermes-gateway.service"
    ALL_OK=false
fi

# Profile gateways (systemd template units)
for p in "${PROFILES[@]}"; do
    STATUS=$(systemctl --user is-active "hermes-gateway@$p.service" 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "active" ]; then
        PID=$(systemctl --user show "hermes-gateway@$p.service" --property=MainPID 2>/dev/null | cut -d= -f2)
        echo "    ✅ [$p] Gateway running — PID $PID."
    else
        echo "    ❌ [$p] Gateway NOT running (status: $STATUS)."
        echo "       Fix: systemctl --user start hermes-gateway@$p.service"
        ALL_OK=false
    fi
done

# ── 3. Summary ──
echo ""
if [ "$ALL_OK" = "true" ]; then
    echo "✅ ALL session DBs and gateways healthy — $DB_TYPE ($DB_NAME) + ${#PROFILES[@]} profile gateways + default."
else
    echo "⚠ Some issues found — see details above."
fi

exit 0
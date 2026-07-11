#!/usr/bin/env bash
# restart-profile-gateway.sh — Restart one or all Hermes profile gateways
# Uses user-level systemd services (hermes-gateway@<profile>.service)
#
# Usage:
#   restart-gateway.sh                     # Auto-detect: restart calling profile (or all if called from main)
#   restart-profile-gateway.sh <profile>   # Restart one profile explicitly
#   restart-profile-gateway.sh all         # Restart ALL profile gateways
#   restart-profile-gateway.sh --status    # Show status of all gateways (read-only)
#
# Symlinked to each profile's scripts/ directory for per-profile access.
# When called via a profile symlink, defaults to restarting that profile.
#
# CONFIG: Edit the PROFILES array below to match your setup.

set -euo pipefail

# ── User Profiles (edit to match your profile names) ──
PROFILES=(crm-manager hr-manager marketing-manager product-manager project-manager)

# Detect calling profile from symlink path
SCRIPT_PATH=$(readlink -f "$0")
CALLING_PROFILE=$(echo "$SCRIPT_PATH" | grep -oP 'profiles/\K[^/]+(?=/scripts)' || echo "")

restart_one() {
    local profile="$1"
    local unit="hermes-gateway@${profile}.service"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restarting $profile..."
    systemctl --user restart "$unit"
    sleep 2

    if systemctl --user is-active --quiet "$unit"; then
        local pid mem mem_mb
        pid=$(systemctl --user show -p MainPID "$unit" 2>/dev/null | cut -d= -f2)
        mem=$(systemctl --user show -p MemoryCurrent "$unit" 2>/dev/null | cut -d= -f2)
        mem_mb=$(( ${mem:-0} / 1048576 ))
        echo "  ✅ $profile: running (PID $pid, ${mem_mb}M)"
    else
        echo "  ❌ $profile: FAILED to start"
        journalctl --user -u "$unit" --since "30 seconds ago" --no-pager 2>/dev/null | tail -5
        return 1
    fi
}

show_status() {
    echo ""
    echo "=== Gateway Status ==="
    printf "  %-20s %-10s %-10s %s\n" "PROFILE" "STATUS" "PID" "MEMORY"
    for profile in "${PROFILES[@]}"; do
        local unit="hermes-gateway@${profile}.service"
        local status pid mem mem_mb
        status=$(systemctl --user is-active "$unit" 2>/dev/null || echo "unknown")
        pid=$(systemctl --user show -p MainPID "$unit" 2>/dev/null | cut -d= -f2)
        mem=$(systemctl --user show -p MemoryCurrent "$unit" 2>/dev/null | cut -d= -f2)
        mem_mb=$(( ${mem:-0} / 1048576 ))
        printf "  %-20s %-10s %-10s %sM\n" "$profile" "$status" "$pid" "$mem_mb"
    done
    # Default gateway (no profile)
    local status pid mem mem_mb
    status=$(systemctl --user is-active hermes-gateway.service 2>/dev/null || echo "unknown")
    pid=$(systemctl --user show -p MainPID hermes-gateway.service 2>/dev/null | cut -d= -f2)
    mem=$(systemctl --user show -p MemoryCurrent hermes-gateway.service 2>/dev/null | cut -d= -f2)
    mem_mb=$(( ${mem:-0} / 1048576 ))
    printf "  %-20s %-10s %-10s %sM\n" "default" "$status" "$pid" "$mem_mb"
}

# Main
case "${1:-}" in
    --status)
        show_status
        ;;
    all)
        echo "=== Restarting ALL profile gateways ==="
        failed=0
        for profile in "${PROFILES[@]}"; do
            restart_one "$profile" || ((failed++))
        done
        show_status
        if [ "$failed" -gt 0 ]; then
            echo "⚠️  $failed profile(s) failed to restart"
            exit 1
        fi
        ;;
    "")
        # No arg — auto-detect from symlink path
        if [ -n "$CALLING_PROFILE" ]; then
            restart_one "$CALLING_PROFILE"
        else
            echo "=== No profile detected (called from main). Restarting ALL ==="
            for profile in "${PROFILES[@]}"; do
                restart_one "$profile"
            done
        fi
        show_status
        ;;
    *)
        # Validate profile name
        if [[ " ${PROFILES[*]} " =~ " ${1} " ]]; then
            restart_one "$1"
        else
            echo "ERROR: Unknown profile '$1'"
            echo "Valid profiles: ${PROFILES[*]} or 'all' or '--status'"
            exit 1
        fi
        show_status
        ;;
esac
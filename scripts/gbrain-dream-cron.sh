#!/usr/bin/env bash
# gbrain-dream-cron.sh — Run the 3-phase GBrain dream cycle
set -euo pipefail

# ── Resolve gbrain binary ──────────────────────────────────────────────────
GBRAIN=""
if command -v gbrain &>/dev/null; then
  GBRAIN="gbrain"
elif [ -x "$HOME/.bun/bin/gbrain" ]; then
  GBRAIN="$HOME/.bun/bin/gbrain"
else
  echo "[FATAL] gbrain binary not found in PATH or at ~/.bun/bin/gbrain"
  exit 1
fi

# ── Log setup ──────────────────────────────────────────────────────────────
LOG_DIR="$HOME/.gbrain/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/dream-$(date +%Y%m%d).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ── Phase runner — returns 1 on failure (caller handles continuation) ──────
run_phase() {
  local phase_name="$1"
  shift
  log "► Starting phase: $phase_name"
  if "$GBRAIN" autopilot cycle --phase "$phase_name" --yes "$@" >>"$LOG_FILE" 2>&1; then
    log "✅ Phase completed: $phase_name"
    return 0
  else
    log "❌ Phase FAILED: $phase_name (exit code $?)"
    return 1
  fi
}

# ── Log rotation: delete dream logs older than 7 days ──────────────────────
rotate_logs() {
  find "$LOG_DIR" -maxdepth 1 -type f -name 'dream-*.log' -mtime +7 -delete 2>/dev/null
  log "Log rotation: cleaned dream logs older than 7 days"
}

# ── Header ─────────────────────────────────────────────────────────────────
log "═══════════════════════════════════════════════════════════════"
log "GBrain Dream Cycle — 3-phase run"
log "Binary: $GBRAIN"
log "═══════════════════════════════════════════════════════════════"

# ── Track failures across phases ───────────────────────────────────────────
FAILED=0

# ── Phase 1: Consolidate ───────────────────────────────────────────────────
run_phase "consolidate" || FAILED=1

# ── Phase 2: Synthesize ────────────────────────────────────────────────────
run_phase "synthesize" || FAILED=1

# ── Phase 3: Patterns ──────────────────────────────────────────────────────
run_phase "patterns" || FAILED=1

# ── Log rotation ───────────────────────────────────────────────────────────
rotate_logs

# ── Footer ─────────────────────────────────────────────────────────────────
log "═══════════════════════════════════════════════════════════════"
if [ "$FAILED" -eq 1 ]; then
  log "Dream cycle completed with failures — check logs above."
  log "═══════════════════════════════════════════════════════════════"
  exit 1
else
  log "Dream cycle complete — all phases passed."
  log "═══════════════════════════════════════════════════════════════"
fi
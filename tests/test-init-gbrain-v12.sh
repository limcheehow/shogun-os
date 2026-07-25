#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Test Suite: init-gbrain.sh v1.2.0
# Verifies the presence and correctness of new sections:
#   - Ollama + Local Embedding
#   - Schema Pack
#   - Cron Setup
#   - VERSION="1.2.0"
#   - Dry-run executes without errors
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INIT_SCRIPT="$SCRIPT_DIR/scripts/init-gbrain.sh"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo -e "  \033[0;32m✅ PASS\033[0m $1"; }
fail() { FAIL=$((FAIL + 1)); echo -e "  \033[0;31m❌ FAIL\033[0m $1"; }

echo ""
echo -e "\033[0;36m══════════════════════════════════════════════════════\033[0m"
echo -e "\033[0;36m  init-gbrain.sh v1.2.0 Test Suite\033[0m"
echo -e "\033[0;36m══════════════════════════════════════════════════════\033[0m"
echo ""

# ── Test 1: VERSION is 1.2.0 ─────────────────────────────────────────

echo -e "\033[0;36m━━━ Test: VERSION ━━━\033[0m"

if grep -q 'VERSION="1.2.0"' "$INIT_SCRIPT"; then
  pass "VERSION is 1.2.0"
else
  fail "VERSION is not 1.2.0"
fi

# ── Test 2: Contains Ollama section ─────────────────────────────────

echo ""
echo -e "\033[0;36m━━━ Test: Ollama Section ━━━\033[0m"

if grep -q "Ollama + Local Embedding" "$INIT_SCRIPT"; then
  pass "Script contains 'Ollama + Local Embedding' section header"
else
  fail "Missing 'Ollama + Local Embedding' section header"
fi

if grep -q "nomic-embed-text" "$INIT_SCRIPT"; then
  pass "Script references nomic-embed-text model"
else
  fail "Missing nomic-embed-text model reference"
fi

if grep -q "ollama pull" "$INIT_SCRIPT"; then
  pass "Script has ollama pull command (dry-run / real)"
else
  fail "Missing ollama pull command"
fi

# ── Test 3: Contains Schema Pack section ────────────────────────────

echo ""
echo -e "\033[0;36m━━━ Test: Schema Pack Section ━━━\033[0m"

if grep -q "Schema Pack" "$INIT_SCRIPT"; then
  pass "Script contains 'Schema Pack' section header"
else
  fail "Missing 'Schema Pack' section header"
fi

if grep -q "shogun-enterprise" "$INIT_SCRIPT"; then
  pass "Script references shogun-enterprise schema pack"
else
  fail "Missing shogun-enterprise schema pack reference"
fi

if grep -q "gbrain schema use" "$INIT_SCRIPT"; then
  pass "Script has 'gbrain schema use' command"
else
  fail "Missing 'gbrain schema use' command"
fi

# ── Test 4: Contains Cron Setup section ─────────────────────────────

echo ""
echo -e "\033[0;36m━━━ Test: Cron Setup Section ━━━\033[0m"

if grep -q "Cron Setup" "$INIT_SCRIPT"; then
  pass "Script contains 'Cron Setup' section header"
else
  fail "Missing 'Cron Setup' section header"
fi

if grep -q "gbrain-dream-cron" "$INIT_SCRIPT"; then
  pass "Script references gbrain-dream-cron"
else
  fail "Missing gbrain-dream-cron reference"
fi

if grep -q "gbrain-backup" "$INIT_SCRIPT"; then
  pass "Script references gbrain-backup"
else
  fail "Missing gbrain-backup reference"
fi

if grep -q "CRON_INSTALLED" "$INIT_SCRIPT"; then
  pass "Script tracks CRON_INSTALLED count"
else
  fail "Missing CRON_INSTALLED tracking variable"
fi

# ── Test 5: Dry-run executes without errors ─────────────────────────

echo ""
echo -e "\033[0;36m━━━ Test: Dry-Run ━━━\033[0m"

# Run dry-run, capturing both stdout and stderr
DRY_RUN_OUTPUT=$(bash "$INIT_SCRIPT" --dry-run 2>&1)
DRY_EXIT=$?

if [[ "$DRY_EXIT" -eq 0 ]]; then
  pass "Dry-run exited with code 0"
else
  fail "Dry-run exited with code $DRY_EXIT (expected 0)"
fi

# Check that all three sections appear in dry-run output
if echo "$DRY_RUN_OUTPUT" | grep -q "Ollama + Local Embedding"; then
  pass "Dry-run output includes 'Ollama + Local Embedding' section"
else
  fail "Dry-run output missing 'Ollama + Local Embedding' section"
fi

if echo "$DRY_RUN_OUTPUT" | grep -q "Schema Pack"; then
  pass "Dry-run output includes 'Schema Pack' section"
else
  fail "Dry-run output missing 'Schema Pack' section"
fi

if echo "$DRY_RUN_OUTPUT" | grep -q "Cron Setup"; then
  pass "Dry-run output includes 'Cron Setup' section"
else
  fail "Dry-run output missing 'Cron Setup' section"
fi

# Check dry-run respects dry-run mode (no real changes)
if echo "$DRY_RUN_OUTPUT" | grep -q "DRY RUN"; then
  pass "Dry-run output shows '[DRY-RUN]' mode indicator"
else
  fail "Dry-run output missing '[DRY-RUN]' mode indicator"
fi

# Check summary includes new fields
if echo "$DRY_RUN_OUTPUT" | grep -q "Ollama"; then
  pass "Summary includes Ollama status"
else
  fail "Summary missing Ollama status"
fi

if echo "$DRY_RUN_OUTPUT" | grep -q "Schema"; then
  pass "Summary includes Schema pack status"
else
  fail "Summary missing Schema pack status"
fi

if echo "$DRY_RUN_OUTPUT" | grep -q "Crons"; then
  pass "Summary includes Crons status"
else
  fail "Summary missing Crons status"
fi

# ── Summary ─────────────────────────────────────────────────────────

echo ""
echo -e "\033[0;36m══════════════════════════════════════════════════════\033[0m"
echo -e "  Results: $PASS passed, $FAIL failed"
echo -e "\033[0;36m══════════════════════════════════════════════════════\033[0m"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
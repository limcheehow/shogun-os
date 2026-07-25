#!/usr/bin/env bash
# =============================================================================
# Test: gbrain-backup.sh
# =============================================================================
set -euo pipefail

SCRIPT="$HOME/shogun-os/scripts/gbrain-backup.sh"
TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    local msg="$1"
    echo "  PASS  | ${msg}"
    TESTS_PASSED=$(($TESTS_PASSED + 1))
}

fail() {
    local msg="$1"
    echo "  FAIL  | ${msg}"
    TESTS_FAILED=$(($TESTS_FAILED + 1))
}

# -------------------------------------------------------
# Test 1: Script exists and is executable
# -------------------------------------------------------
echo ""
echo "[Test 1] Script exists and is executable"

if [ ! -f "$SCRIPT" ]; then
    fail "$SCRIPT does not exist"
elif [ ! -x "$SCRIPT" ]; then
    fail "$SCRIPT is not executable"
else
    pass "$SCRIPT exists and is executable"
fi

# -------------------------------------------------------
# Test 2: Script has proper shebang and set -euo pipefail
# -------------------------------------------------------
echo ""
echo "[Test 2] Shebang and set -euo pipefail"

SHEBANG=$(head -1 "$SCRIPT")
if [[ "$SHEBANG" == "#!/usr/bin/env bash" ]]; then
    pass "Shebang is correct: $SHEBANG"
else
    fail "Shebang is wrong: $SHEBANG"
fi

if grep -q 'set -euo pipefail' "$SCRIPT" 2>/dev/null; then
    pass "Script contains 'set -euo pipefail'"
else
    fail "Script does NOT contain 'set -euo pipefail'"
fi

# -------------------------------------------------------
# Test 3: Script references pg_dump
# -------------------------------------------------------
echo ""
echo "[Test 3] References pg_dump"

PGDUMP_COUNT=$(grep -c 'pg_dump' "$SCRIPT" || true)
if [ "$PGDUMP_COUNT" -ge 1 ]; then
    pass "Script references pg_dump (${PGDUMP_COUNT} occurrence(s))"
else
    fail "Script does NOT reference pg_dump"
fi

# -------------------------------------------------------
# Test 4: Script has retention/pruning logic
# -------------------------------------------------------
echo ""
echo "[Test 4] Retention / pruning logic"

RETENTION_MATCHES=$(grep -c 'RETENTION\|prune\|mtime' "$SCRIPT" || true)
if [ "$RETENTION_MATCHES" -ge 1 ]; then
    pass "Script has retention/pruning logic (${RETENTION_MATCHES} match(es))"
else
    fail "Script does NOT have retention/pruning logic"
fi

# -------------------------------------------------------
# Test 5: Script has TODO git push section
# -------------------------------------------------------
echo ""
echo "[Test 5] TODO git push section"

if grep -qi 'TODO.*git.*push\|git.*push.*TODO\|TODO.*backup.*repo' "$SCRIPT" 2>/dev/null || grep -qi 'git push' "$SCRIPT" 2>/dev/null; then
    pass "Script has TODO git push section"
else
    fail "Script does NOT have a TODO git push section"
fi

# -------------------------------------------------------
# Test 6: Syntax check with bash -n (execution-level verification)
# -------------------------------------------------------
echo ""
echo "[Test 6] Syntax check (bash -n)"

if bash -n "$SCRIPT" 2>/dev/null; then
    pass "bash -n syntax check passed"
else
    fail "bash -n syntax check FAILED"
fi

# -------------------------------------------------------
# Test 7: Backup verification via gzip -t
# -------------------------------------------------------
echo ""
echo "[Test 7] gzip -t backup verification reference"

if grep -q 'gzip -t\|gzip.*--test\|gzip.*test' "$SCRIPT" 2>/dev/null; then
    pass "Script references gzip -t (backup verification)"
else
    fail "Script does NOT reference gzip -t for backup verification"
fi

# -------------------------------------------------------
# Summary
# -------------------------------------------------------
TOTAL=$(($TESTS_PASSED + $TESTS_FAILED))
echo ""
echo "==================================="
echo "  Results: ${TESTS_PASSED}/${TOTAL} passed"
echo "==================================="

if [ "$TESTS_FAILED" -gt 0 ]; then
    exit 1
fi
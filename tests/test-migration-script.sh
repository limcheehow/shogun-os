#!/usr/bin/env bash
# Test: gbrain-migrate-pglite-to-postgres.sh — content and structure verification
set -euo pipefail

PASS=0
FAIL=0
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() {
  PASS=$((PASS + 1))
  echo -e "  ${GREEN}PASS${NC}: $1"
}

fail() {
  FAIL=$((FAIL + 1))
  echo -e "  ${RED}FAIL${NC}: $1"
}

SCRIPT="${HOME}/shogun-os/scripts/gbrain-migrate-pglite-to-postgres.sh"

echo -e "${CYAN}=== test-migration-script.sh ===${NC}"
echo ""

# 1. Script exists and is executable
echo "[Test] Script exists and is executable"
if [ -f "$SCRIPT" ]; then
  pass "Script exists at $SCRIPT"
else
  fail "Script NOT found at $SCRIPT"
fi
if [ -x "$SCRIPT" ]; then
  pass "Script is executable"
else
  fail "Script is NOT executable"
fi

# 2. Has proper shebang and set -euo pipefail
echo "[Test] Shebang and set -euo pipefail"
if head -1 "$SCRIPT" | grep -q "^#!/usr/bin/env bash"; then
  pass "Has correct shebang: #!/usr/bin/env bash"
else
  fail "Shebang is missing or incorrect"
fi
if grep -q "^set -euo pipefail" "$SCRIPT"; then
  pass "Has 'set -euo pipefail'"
else
  fail "Missing 'set -euo pipefail'"
fi

# 3. References key commands: pg_isready, migrate, backup, doctor
echo "[Test] References pg_isready"
if grep -q "pg_isready" "$SCRIPT"; then
  pass "Script references pg_isready for Postgres connectivity check"
else
  fail "Missing reference to pg_isready"
fi

echo "[Test] References migrate command"
if grep -q "migrate" "$SCRIPT"; then
  pass "Script references gbrain migrate command"
else
  fail "Missing reference to migrate"
fi

echo "[Test] References backup"
if grep -q "backup\|cp -a\|Backup" "$SCRIPT"; then
  pass "Script creates backup of ~/.gbrain"
else
  fail "Missing backup logic"
fi

echo "[Test] References doctor"
if grep -q "doctor" "$SCRIPT"; then
  pass "Script runs gbrain doctor for verification"
else
  fail "Missing reference to gbrain doctor"
fi

# 4. Has color helper functions
echo "[Test] Color helper functions"
for func in ok info warn err; do
  if grep -q "^${func}()" "$SCRIPT"; then
    pass "Has color helper function: ${func}"
  else
    fail "Missing color helper function: ${func}"
  fi
done

# 5. Has color variable definitions
echo "[Test] Color variable definitions"
for color_var in RED GREEN YELLOW CYAN NC; do
  if grep -q "${color_var}=" "$SCRIPT"; then
    pass "Has color variable: ${color_var}"
  else
    fail "Missing color variable: ${color_var}"
  fi
done

# 6. Has rollback/restore instructions
echo "[Test] Rollback / restore instructions"
if grep -qi "restore\|rollback\|RESTORE INSTRUCTIONS" "$SCRIPT"; then
  pass "Script has restore/rollback instructions"
else
  fail "Missing restore/rollback instructions"
fi

# 7. Environment variable configuration
echo "[Test] Configurable via environment variables"
for var in GBRAIN_DB_HOST GBRAIN_DB_PORT GBRAIN_DB_USER GBRAIN_DB_NAME; do
  if grep -q "${var}=" "$SCRIPT"; then
    pass "Script supports env var: ${var}"
  else
    fail "Missing env var: ${var}"
  fi
done

# 8. Checks engine before proceeding
echo "[Test] Engine check before migration"
if grep -q "config get engine" "$SCRIPT"; then
  pass "Script checks current engine via 'gbrain config get engine'"
else
  fail "Missing engine check"
fi

# 9. Exits early if already postgres
echo "[Test] Early exit if already postgres"
if grep -q "already.*postgres\|postgres.*nothing" "$SCRIPT"; then
  pass "Script exits early with success if already postgres"
else
  fail "Missing early-exit for already-postgres engine"
fi

# 10. pgvector extension check
echo "[Test] pgvector extension check"
if grep -q "pgvector\|CREATE EXTENSION.*vector\|vector" "$SCRIPT"; then
  pass "Script ensures pgvector extension exists"
else
  fail "Missing pgvector extension check"
fi

# 11. Verification after migration
echo "[Test] Post-migration verification"
if grep -q "gbrain stats" "$SCRIPT"; then
  pass "Script runs gbrain stats after migration"
else
  fail "Missing gbrain stats verification"
fi

# 12. Syntax check with bash -n (execution-level verification)
echo ""
echo "[Test] Syntax check (bash -n)"
SCRIPT_CONTENT=$(cat "$SCRIPT")
if echo "$SCRIPT_CONTENT" | bash -n 2>/dev/null; then
  pass "bash -n syntax check passed"
else
  fail "bash -n syntax check FAILED"
fi

# 13. PGPASSWORD support check
echo ""
echo "[Test] PGPASSWORD support"
if grep -q "PGPASSWORD" "$SCRIPT"; then
  pass "Script supports PGPASSWORD for authentication"
else
  fail "Script does NOT support PGPASSWORD"
fi

echo ""
echo -e "${CYAN}=== Results: $PASS passed, $FAIL failed ===${NC}"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
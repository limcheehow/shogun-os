#!/usr/bin/env bash
# Test: PostgreSQL installation for gbrain (psql, database, pgvector)
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

echo -e "${CYAN}=== test-pg-install.sh ===${NC}"
echo ""

# 1. psql binary exists in PATH
echo "[Test] psql binary in PATH"
if command -v psql &>/dev/null; then
  pass "psql binary found at $(command -v psql) — version: $(psql --version 2>&1 | head -1)"
else
  fail "psql binary not found in PATH (PostgreSQL may not be installed)"
fi

# 2. PostgreSQL service is accepting connections
echo "[Test] pg_isready"
OUTPUT=$(pg_isready 2>&1) || true
if echo "$OUTPUT" | grep -q "accepting connections"; then
  pass "pg_isready: $OUTPUT"
else
  fail "pg_isready failed: $OUTPUT"
fi

# 3. gbrain database user exists
echo "[Test] gbrain database user"
if psql -U gbrain -c "SELECT 1" &>/dev/null; then
  pass "gbrain database user exists and can connect"
else
  fail "Cannot connect as gbrain user (peer/trust auth may not be configured)"
fi

# 4. gbrain database exists
echo "[Test] gbrain database existence"
if psql -U gbrain -d gbrain -c "SELECT 1" &>/dev/null; then
  pass "gbrain database exists and is accessible"
else
  fail "Cannot access gbrain database (psql -U gbrain -d gbrain failed)"
fi

# 5. pgvector extension is enabled
echo "[Test] pgvector extension in gbrain database"
VECTOR_CHECK=$(psql -U gbrain -d gbrain -t -c "SELECT count(*) FROM pg_extension WHERE extname='vector';" 2>/dev/null | tr -d ' ')
if [ "$VECTOR_CHECK" = "1" ]; then
  pass "vector extension is enabled in gbrain database"
else
  VECTOR_VER=$(psql -U gbrain -d gbrain -t -c "SELECT extversion FROM pg_extension WHERE extname='vector';" 2>/dev/null | tr -d ' ' || echo "not found")
  fail "vector extension NOT enabled in gbrain database (version: $VECTOR_VER)"
fi

echo ""
echo -e "${CYAN}=== Results: $PASS passed, $FAIL failed ===${NC}"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
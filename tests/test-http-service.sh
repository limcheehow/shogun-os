#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

PASS_COUNT=0
FAIL_COUNT=0

pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo "  PASS: $1"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "  FAIL: $1"; }

echo "=== Test: GBrain HTTP MCP Service ==="

# --- File existence ---
echo ""
echo "--- File existence ---"

if [ -f "$REPO_DIR/scripts/gbrain-http-service.sh" ]; then
  pass "scripts/gbrain-http-service.sh exists"
else
  fail "scripts/gbrain-http-service.sh exists"
fi

<<<<<<< HEAD
if [ -f "$REPO_DIR/scripts/gbrain-http@.service" ]; then
  pass "scripts/gbrain-http@.service exists"
else
  fail "scripts/gbrain-http@.service exists"
=======
if [ -f "$REPO_DIR/scripts/gbrain-http.service" ]; then
  pass "scripts/gbrain-http.service exists"
else
  fail "scripts/gbrain-http.service exists"
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
fi

# --- Executable check ---
echo ""
echo "--- Executable check ---"

if [ -x "$REPO_DIR/scripts/gbrain-http-service.sh" ]; then
  pass "scripts/gbrain-http-service.sh is executable"
else
  fail "scripts/gbrain-http-service.sh is executable"
fi

# --- Service script content ---
echo ""
echo "--- Service script content ---"

if grep -q 'serve --http' "$REPO_DIR/scripts/gbrain-http-service.sh"; then
  pass "Service script references 'serve --http'"
else
  fail "Service script references 'serve --http'"
fi

if grep -q 'set -euo pipefail' "$REPO_DIR/scripts/gbrain-http-service.sh"; then
  pass "Service script has 'set -euo pipefail'"
else
  fail "Service script has 'set -euo pipefail'"
fi

if grep -q 'GBRAIN_HTTP_PORT' "$REPO_DIR/scripts/gbrain-http-service.sh"; then
  pass "Service script references GBRAIN_HTTP_PORT env var"
else
  fail "Service script references GBRAIN_HTTP_PORT env var"
fi

if grep -q 'GBRAIN_HTTP_HOST' "$REPO_DIR/scripts/gbrain-http-service.sh"; then
  pass "Service script references GBRAIN_HTTP_HOST env var"
else
  fail "Service script references GBRAIN_HTTP_HOST env var"
fi

if grep -q '\.bun/bin/gbrain' "$REPO_DIR/scripts/gbrain-http-service.sh"; then
  pass "Service script has fallback path ~/.bun/bin/gbrain"
else
  fail "Service script has fallback path ~/.bun/bin/gbrain"
fi

# --- Systemd unit file content ---
echo ""
echo "--- Systemd unit file content ---"

<<<<<<< HEAD
if grep -q '\[Unit\]' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q '\[Unit\]' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "Systemd file has [Unit] section"
else
  fail "Systemd file has [Unit] section"
fi

<<<<<<< HEAD
if grep -q '\[Service\]' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q '\[Service\]' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "Systemd file has [Service] section"
else
  fail "Systemd file has [Service] section"
fi

<<<<<<< HEAD
if grep -q '\[Install\]' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q '\[Install\]' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "Systemd file has [Install] section"
else
  fail "Systemd file has [Install] section"
fi

<<<<<<< HEAD
DESCRIPTION_LINE=$(grep 'Description=' "$REPO_DIR/scripts/gbrain-http@.service" || true)
=======
DESCRIPTION_LINE=$(grep 'Description=' "$REPO_DIR/scripts/gbrain-http.service" || true)
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
if echo "$DESCRIPTION_LINE" | grep -q 'GBrain HTTP MCP Server'; then
  pass "Description is 'GBrain HTTP MCP Server'"
else
  fail "Description is 'GBrain HTTP MCP Server'"
fi

<<<<<<< HEAD
# After= targets postgresql (hard dependency), Wants=ollama (soft dependency)
if grep -q 'After=postgresql.service' "$REPO_DIR/scripts/gbrain-http@.service" && \
   grep -q 'Wants=ollama.service' "$REPO_DIR/scripts/gbrain-http@.service"; then
  pass "After=postgresql.service (hard), Wants=ollama.service (soft)"
else
  fail "After=postgresql.service (hard), Wants=ollama.service (soft)"
fi

if grep -q 'Environment=GBRAIN_HTTP_PORT=3100' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q 'After=postgresql.service ollama.service' "$REPO_DIR/scripts/gbrain-http.service"; then
  pass "After includes postgresql.service and ollama.service"
else
  fail "After includes postgresql.service and ollama.service"
fi

if grep -q 'Environment=GBRAIN_HTTP_PORT=3100' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "Environment sets GBRAIN_HTTP_PORT=3100"
else
  fail "Environment sets GBRAIN_HTTP_PORT=3100"
fi

EXPECTED_EXECSTART='%h/shogun-os/scripts/gbrain-http-service.sh'
<<<<<<< HEAD
if grep -q "ExecStart=$EXPECTED_EXECSTART" "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q "ExecStart=$EXPECTED_EXECSTART" "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "ExecStart references correct path"
else
  fail "ExecStart references correct path"
  echo "       Expected: ExecStart=$EXPECTED_EXECSTART"
<<<<<<< HEAD
  echo "       Actual:   $(grep 'ExecStart=' "$REPO_DIR/scripts/gbrain-http@.service" || echo 'not found')"
fi

if grep -q 'User=%i' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
  echo "       Actual:   $(grep 'ExecStart=' "$REPO_DIR/scripts/gbrain-http.service" || echo 'not found')"
fi

if grep -q 'User=%i' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "User=%i (template unit)"
else
  fail "User=%i (template unit)"
fi

<<<<<<< HEAD
if grep -q 'WorkingDirectory=%h' "$REPO_DIR/scripts/gbrain-http@.service"; then
  pass "WorkingDirectory=%h"
else
  fail "WorkingDirectory=%h"
fi

if grep -q 'Restart=on-failure' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q 'Restart=on-failure' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "Restart=on-failure"
else
  fail "Restart=on-failure"
fi

<<<<<<< HEAD
if grep -q 'RestartSec=5' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q 'RestartSec=5' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "RestartSec=5"
else
  fail "RestartSec=5"
fi

<<<<<<< HEAD
if grep -q 'WantedBy=multi-user.target' "$REPO_DIR/scripts/gbrain-http@.service"; then
=======
if grep -q 'WantedBy=multi-user.target' "$REPO_DIR/scripts/gbrain-http.service"; then
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
  pass "WantedBy=multi-user.target"
else
  fail "WantedBy=multi-user.target"
fi

<<<<<<< HEAD
# --- Execution-level verification ---
echo ""
echo "--- Execution-level verification ---"

# Syntax check with bash -n
if bash -n "$REPO_DIR/scripts/gbrain-http-service.sh" 2>/dev/null; then
  pass "bash -n syntax check passed for gbrain-http-service.sh"
else
  fail "bash -n syntax check FAILED for gbrain-http-service.sh"
fi

# systemd-analyze verify if available
if command -v systemd-analyze &>/dev/null; then
  if systemd-analyze verify "$REPO_DIR/scripts/gbrain-http@.service" 2>/dev/null; then
    pass "systemd-analyze verify passed for gbrain-http@.service"
  else
    fail "systemd-analyze verify FAILED for gbrain-http@.service"
  fi
else
  pass "systemd-analyze not available — skipped systemd unit verification"
fi

=======
>>>>>>> e91dd72 (v3.11.0: GBrain production integration)
# --- Summary ---
echo ""
echo "================================"
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "================================"

if [ "$FAIL_COUNT" -eq 0 ]; then
  exit 0
else
  exit 1
fi
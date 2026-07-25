#!/usr/bin/env bash
# Test: Ollama installation and nomic-embed-text model availability
set -euo pipefail

PASS=0
FAIL=0
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

pass() {
  PASS=$((PASS + 1))
  echo -e "  ${GREEN}PASS${NC}: $1"
}

fail() {
  FAIL=$((FAIL + 1))
  echo -e "  ${RED}FAIL${NC}: $1"
}

echo "=== test-ollama-setup.sh ==="
echo ""

# 1. ollama binary exists in PATH
echo "[Test] ollama binary in PATH"
if command -v ollama &>/dev/null; then
  pass "ollama binary found at $(command -v ollama)"
else
  fail "ollama binary not found in PATH"
fi

# 2. ollama --version returns successfully
echo "[Test] ollama --version"
if ollama --version &>/dev/null; then
  pass "ollama --version: $(ollama --version 2>&1)"
else
  fail "ollama --version failed"
fi

# 3. Ollama service is running (systemd OR user process)
echo "[Test] ollama service running"
if systemctl is-active --quiet ollama 2>/dev/null; then
  pass "ollama service is active (systemd)"
elif curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  pass "ollama server is running and responding on port 11434"
else
  fail "ollama service is not running (checked systemd and localhost:11434)"
fi

# 4. nomic-embed-text model is available via API
echo "[Test] nomic-embed-text model via API"
if curl -sf http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
if any('nomic-embed-text' in m for m in models):
    print('found')
    sys.exit(0)
else:
    print('not found')
    sys.exit(1)
" 2>/dev/null; then
  pass "nomic-embed-text model listed in Ollama API"
else
  fail "nomic-embed-text model NOT found via Ollama API (curl http://localhost:11434/api/tags)"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
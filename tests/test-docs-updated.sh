#!/usr/bin/env bash
# test-docs-updated.sh — Verify ARCHITECTURE.md and CHANGELOG.md updates for GBrain Production Integration
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

ARCH="$REPO_DIR/ARCHITECTURE.md"
CHANGELOG="$REPO_DIR/CHANGELOG.md"

pass=0
fail=0

pass_one() {
  echo "  ✅ $1"
  pass=$((pass + 1))
}

fail_one() {
  echo "  ❌ $1"
  fail=$((fail + 1))
}

check_file() {
  local label="$1"
  shift
  if test "$@"; then
    pass_one "$label"
  else
    fail_one "$label"
  fi
}

echo "═══════════════════════════════════════════════════════════════"
echo "Test: Docs Updated for GBrain Production Integration"
echo "═══════════════════════════════════════════════════════════════"

# 1) ARCHITECTURE.md exists
check_file "ARCHITECTURE.md exists" -f "$ARCH"

# 2) CHANGELOG.md exists
check_file "CHANGELOG.md exists" -f "$CHANGELOG"

echo ""
echo "─── ARCHITECTURE.md checks ───"

# 3) Contains "Ollama"
if grep -q 'Ollama' "$ARCH"; then
  pass_one "ARCHITECTURE.md contains 'Ollama'"
else
  fail_one "ARCHITECTURE.md contains 'Ollama'"
fi

# 4) Contains "nomic-embed-text"
if grep -q 'nomic-embed-text' "$ARCH"; then
  pass_one "ARCHITECTURE.md contains 'nomic-embed-text'"
else
  fail_one "ARCHITECTURE.md contains 'nomic-embed-text'"
fi

# 5) Contains "shogun-enterprise"
if grep -q 'shogun-enterprise' "$ARCH"; then
  pass_one "ARCHITECTURE.md contains 'shogun-enterprise'"
else
  fail_one "ARCHITECTURE.md contains 'shogun-enterprise'"
fi

# 6) Contains "3100" (HTTP MCP port)
if grep -q '3100' "$ARCH"; then
  pass_one "ARCHITECTURE.md contains '3100' (HTTP MCP port)"
else
  fail_one "ARCHITECTURE.md contains '3100' (HTTP MCP port)"
fi

# 7) Source tree diagram preserved (shared/ + departments)
if grep -q 'shared/' "$ARCH" && grep -q 'engineering/' "$ARCH"; then
  pass_one "ARCHITECTURE.md preserves source tree diagram (shared/ + departments)"
else
  fail_one "ARCHITECTURE.md preserves source tree diagram (shared/ + departments)"
fi

# 8) Federated read explanation preserved
if grep -q 'Federated read' "$ARCH"; then
  pass_one "ARCHITECTURE.md preserves federated read explanation"
else
  fail_one "ARCHITECTURE.md preserves federated read explanation"
fi

# 9) pg_dump backup mentioned
if grep -q 'pg_dump' "$ARCH"; then
  pass_one "ARCHITECTURE.md mentions pg_dump backup"
else
  fail_one "ARCHITECTURE.md mentions pg_dump backup"
fi

# 10) PostgreSQL 16 mentioned
if grep -q 'PostgreSQL 16' "$ARCH"; then
  pass_one "ARCHITECTURE.md mentions PostgreSQL 16"
else
  fail_one "ARCHITECTURE.md mentions PostgreSQL 16"
fi

# 11) pgvector mentioned
if grep -q 'pgvector' "$ARCH"; then
  pass_one "ARCHITECTURE.md mentions pgvector extension"
else
  fail_one "ARCHITECTURE.md mentions pgvector extension"
fi

# 12) Dream cycle mentioned
if grep -q 'Dream cycle' "$ARCH"; then
  pass_one "ARCHITECTURE.md mentions dream cycle maintenance"
else
  fail_one "ARCHITECTURE.md mentions dream cycle maintenance"
fi

echo ""
echo "─── CHANGELOG.md checks ───"

# 13) Contains "v3.11.0"
if grep -q 'v3.11.0\|3\.11\.0' "$CHANGELOG"; then
  pass_one "CHANGELOG.md contains 'v3.11.0'"
else
  fail_one "CHANGELOG.md contains 'v3.11.0'"
fi

# 14) Contains "Ollama"
if grep -q 'Ollama' "$CHANGELOG"; then
  pass_one "CHANGELOG.md contains 'Ollama'"
else
  fail_one "CHANGELOG.md contains 'Ollama'"
fi

# 15) Contains GBrain Production Integration as a heading
if grep -q 'GBrain Production Integration' "$CHANGELOG"; then
  pass_one "CHANGELOG.md has 'GBrain Production Integration' section"
else
  fail_one "CHANGELOG.md has 'GBrain Production Integration' section"
fi

# 16) Contains shogun-enterprise
if grep -q 'shogun-enterprise' "$CHANGELOG"; then
  pass_one "CHANGELOG.md mentions shogun-enterprise schema pack"
else
  fail_one "CHANGELOG.md mentions shogun-enterprise schema pack"
fi

# 17) Contains pg_dump
if grep -q 'pg_dump' "$CHANGELOG"; then
  pass_one "CHANGELOG.md mentions pg_dump backups"
else
  fail_one "CHANGELOG.md mentions pg_dump backups"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Results: $pass passed, $fail failed"
echo "═══════════════════════════════════════════════════════════════"

if [ "$fail" -gt 0 ]; then
  exit 1
fi
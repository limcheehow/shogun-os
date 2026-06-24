#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Company OS — Install Verification Suite
# ──────────────────────────────────────────────────────────────────────────
# Checks that all Company OS assets are correctly installed under ~/.hermes/
# after running install.sh.
#
# Usage:
#   ./scripts/verify-install.sh          # Full verification
#   ./scripts/verify-install.sh --quick  # Skip expensive checks
#   ./scripts/verify-install.sh --fix    # Attempt auto-fix for missing items
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"

QUICK=false
FIX=false
PASS=0
FAIL=0
WARN=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { PASS=$((PASS + 1)); echo -e "  ${GREEN}✅${NC} $1"; }
warn() { WARN=$((WARN + 1)); echo -e "  ${YELLOW}⚠️${NC} $1"; }
fail() { FAIL=$((FAIL + 1)); echo -e "  ${RED}❌${NC} $1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)  QUICK=true; shift ;;
    --fix)    FIX=true; shift ;;
    --help|-h)
      echo "Usage: $0 [--quick] [--fix]"
      echo "  --quick  Skip expensive checks (skill validation, script syntax)"
      echo "  --fix    Attempt to re-install missing items"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Company OS — Install Verification${NC}"
echo -e "${CYAN}  Hermes home: ${HERMES_HOME}${NC}"
[[ "$QUICK" == true ]] && echo -e "${YELLOW}  Quick mode — skipping expensive checks${NC}"
[[ "$FIX" == true ]] && echo -e "${YELLOW}  Fix mode enabled — will attempt repairs${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

# ── 1. Skills ────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Skills ━━━${NC}"

check_skill() {
  local name="$1"
  local path="$HERMES_HOME/skills/$name"
  if [[ -d "$path" ]]; then
    if [[ -f "$path/SKILL.md" ]]; then
      ok "Skill installed: $name"
    else
      fail "Skill directory exists but missing SKILL.md: $name"
    fi
  else
    fail "Skill not found: $name"
    if [[ "$FIX" == true && -d "$REPO_ROOT/skills/$name" ]]; then
      mkdir -p "$HERMES_HOME/skills"
      cp -r "$REPO_ROOT/skills/$name" "$HERMES_HOME/skills/$name"
      ok "[FIX] Re-installed: $name"
    fi
  fi
}

check_skill "department-scrum"
check_skill "brain-ingest-pipeline"

echo ""

# ── 2. Scripts ───────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Scripts ━━━${NC}"

check_script() {
  local name="$1"
  local path="$HERMES_HOME/scripts/$name"
  if [[ -f "$path" ]]; then
    ok "Script installed: $name"

    # Validate Python syntax (skip in quick mode)
    if [[ "$QUICK" != true && "$name" == *.py ]]; then
      if python3 -c "import py_compile; py_compile.compile('$path', doraise=True)" 2>/dev/null; then
        ok "  └─ Syntax check passed: $name"
      else
        fail "  └─ Syntax error in: $name"
      fi
    fi
  else
    fail "Script not found: $path"
    if [[ "$FIX" == true ]]; then
      # Try to find it in the repo
      local found
      found=$(find "$REPO_ROOT" -name "$name" -type f 2>/dev/null | head -1)
      if [[ -n "$found" ]]; then
        mkdir -p "$HERMES_HOME/scripts"
        cp "$found" "$HERMES_HOME/scripts/$name"
        chmod +x "$HERMES_HOME/scripts/$name"
        ok "[FIX] Installed: $name"
      fi
    fi
  fi
}

# All scripts that install.sh would install
check_script "send-scrum-dms.py"
check_script "check-scrum-replies.py"
check_script "test-scrum-cross-dept.py"
check_script "gmail-triage.py"
check_script "collect-calendar.py"
check_script "switch-profile.py"

echo ""

# ── 3. Configs ───────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Configs ━━━${NC}"

if [[ -f "$HERMES_HOME/config/gmail-batches.json" ]]; then
  ok "Gmail batch config installed"
  # Validate JSON
  if jq . "$HERMES_HOME/config/gmail-batches.json" > /dev/null 2>&1; then
    ok "  └─ Valid JSON"
  else
    fail "  └─ Invalid JSON"
  fi
else
  fail "Gmail batch config not found: $HERMES_HOME/config/gmail-batches.json"
  if [[ "$FIX" == true && -f "$REPO_ROOT/examples/brain-ingest-configs/gmail-batches.json" ]]; then
    mkdir -p "$HERMES_HOME/config"
    cp "$REPO_ROOT/examples/brain-ingest-configs/gmail-batches.json" "$HERMES_HOME/config/gmail-batches.json"
    ok "[FIX] Installed gmail batch config"
  fi
fi

echo ""

# ── 4. Symlinks ──────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Symlinks ━━━${NC}"

if [[ -L "$HERMES_HOME/service-account-key.json" ]]; then
  local target
  target="$(readlink "$HERMES_HOME/service-account-key.json")"
  if [[ -f "$target" ]]; then
    ok "SA-DWD symlink: $HERMES_HOME/service-account-key.json → $target"
  else
    warn "SA-DWD symlink exists but target missing: $target"
  fi
elif [[ -f "$HERMES_HOME/service-account-key.json" ]]; then
  warn "SA-DWD key exists but is a regular file, not a symlink (should be symlink to ~/.hermes/secrets/google-dwd-sa.json)"
else
  warn "SA-DWD symlink not found (install.sh creates it when ~/.hermes/secrets/google-dwd-sa.json exists)"
fi

echo ""

# ── 5. Hermes Health ────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Hermes Health ━━━${NC}"

if command -v hermes &> /dev/null; then
  ok "Hermes CLI available: $(hermes --version 2>&1 | head -1)"

  # Check skills are recognized by Hermes (not installed via CLI, but visible)
  if [[ "$QUICK" != true ]]; then
    local skills_output
    skills_output=$(hermes skills list 2>&1 || true)
    for skill in "department-scrum" "brain-ingest-pipeline" "slack-formatting" "brain-compliance" "profile-enrichment" "gbrain-operations"; do
      if echo "$skills_output" | grep -qi "$skill"; then
        ok "  └─ Hermes recognizes skill: $skill"
      else
        warn "  └─ Skill not in hermes skills list (may need 'hermes skills install'): $skill"
      fi
    done
  fi
else
  warn "Hermes CLI not found in PATH (skills are installed but not yet accessible via hermes)"
fi

echo ""

# ── 6. GBrain Connectivity ─────────────────────────────────────────────
echo -e "${CYAN}━━━ GBrain MCP Connectivity ━━━${NC}"

if command -v hermes &> /dev/null; then
  if hermes mcp list 2>&1 | grep -qi "gbrain"; then
    ok "GBrain MCP server is configured"

    # Test: can we query gbrain (if Hermes is running)
    if [[ "$QUICK" != true ]]; then
      local gbrain_test
      gbrain_test=$(hermes chat -q "mcp_gbrain_get_health" --quiet 2>&1 || true)
      if echo "$gbrain_test" | grep -qi "page_count\|brain_score\|version"; then
        ok "  └─ gbrain MCP responds: connected"
      else
        warn "  └─ gbrain MCP configured but query failed (gateway may not be running)"
      fi
    fi
  else
    warn "GBrain MCP server not configured — run gbrain serve and add to hermes mcp"
  fi

  # Check stock-scanner MCP
  if hermes mcp list 2>&1 | grep -qi "stock-scanner"; then
    ok "stock-scanner MCP server is configured"
    if [[ "$QUICK" != true ]]; then
      local stock_test
      stock_test=$(hermes chat -q "mcp_stock_scanner_tradingview_market_indices" --quiet 2>&1 || true)
      if echo "$stock_test" | grep -qi "VIX\|S&P\|NASDAQ"; then
        ok "  └─ stock-scanner MCP responds: connected"
      else
        warn "  └─ stock-scanner MCP configured but query failed"
      fi
    fi
  else
    info "stock-scanner MCP is optional — skip if not needed"
  fi
else
  warn "Hermes CLI not found — cannot test MCP connectivity"
fi

echo ""

# ── 7. Repo Integrity ───────────────────────────────────────────────────
echo -e "${CYAN}━━━ Repo Integrity ━━━${NC}"

# Verify no old paths remain
if [[ ! -d "$REPO_ROOT/plugins" ]]; then
  ok "No old plugins/ directory"
else
  warn "Old plugins/ directory still exists"
fi

if [[ ! -d "$REPO_ROOT/skills/shared" ]]; then
  ok "skills/ is flat (no shared/ subdirectory)"
else
  fail "skills/shared/ still exists — run phase 1 restructure"
fi

if [[ ! -f "$REPO_ROOT/recipes/email-to-brain.md" ]]; then
  ok "Old email-to-brain.md recipe removed"
else
  warn "Old recipe still exists: recipes/email-to-brain.md"
fi

if [[ ! -f "$REPO_ROOT/recipes/calendar-to-brain.md" ]]; then
  ok "Old calendar-to-brain.md recipe removed"
else
  warn "Old recipe still exists: recipes/calendar-to-brain.md"
fi

# Verify docs/ exists
if [[ -d "$REPO_ROOT/docs" ]]; then
  ok "docs/ directory present"
else
  warn "docs/ directory missing — run Phase 7"
fi

echo ""

# ── Summary ──────────────────────────────────────────────────────────────
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}Passed:${NC} $PASS  ${YELLOW}Warnings:${NC} $WARN  ${RED}Failed:${NC} $FAIL"
if [[ "$FAIL" -eq 0 ]]; then
  echo -e "  ${GREEN}✅ All checks passed${NC}"
else
  echo -e "  ${YELLOW}Some checks failed. Run with --fix to attempt repairs.${NC}"
fi
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

exit $FAIL
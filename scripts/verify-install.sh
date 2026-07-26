#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Shogun OS — Install Verification Suite
# ──────────────────────────────────────────────────────────────────────────
# Checks that all Shogun OS assets are correctly installed under HERMES_HOME
# after running install.sh.
#
# Usage:
#   ./scripts/verify-install.sh          # Full verification
#   ./scripts/verify-install.sh --quick  # Skip expensive checks
#   ./scripts/verify-install.sh --fix    # Attempt auto-fix for missing items
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Resolve Python interpreter (python3 is absent/unusable on many Windows setups)
if command -v python >/dev/null 2>&1 && python -c 'import sys' >/dev/null 2>&1; then
  PYTHON=python
elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
  PYTHON=python3
elif command -v py >/dev/null 2>&1; then
  PYTHON="py -3"
else
  PYTHON=python
fi

# Resolve Hermes home (Windows Hermes uses AppData/Local/hermes, not ~/.hermes)
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
if [[ ! -d "$HERMES_HOME" && -d "$HOME/AppData/Local/hermes" ]]; then
  HERMES_HOME="$HOME/AppData/Local/hermes"
fi
# Native Windows Python cannot read MSYS-style /c/... paths — normalize to a
# Windows path (C:\...) so py_compile and json.tool work under Git Bash.
if command -v cygpath >/dev/null 2>&1; then
  HERMES_HOME_WIN="$(cygpath -w "$HERMES_HOME" 2>/dev/null || echo "$HERMES_HOME")"
else
  HERMES_HOME_WIN="$HERMES_HOME"
fi
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
info() { echo -e "  ${CYAN}💡${NC} $1"; }

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
echo -e "${CYAN}  Shogun OS — Install Verification${NC}"
echo -e "${CYAN}  Hermes home: ${HERMES_HOME}${NC}"
[[ "$QUICK" == true ]] && echo -e "${YELLOW}  Quick mode — skipping expensive checks${NC}"
[[ "$FIX" == true ]] && echo -e "${YELLOW}  Fix mode enabled — will attempt repairs${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

# ── 1. Skills ────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Skills ━━━${NC}"

check_skill() {
  local name="$1"
  local subpath="${2:-$1}"  # default to flat name, accept nested path
  local path="$HERMES_HOME/skills/$subpath"
  if [[ -d "$path" ]]; then
    if [[ -f "$path/SKILL.md" ]]; then
      ok "Skill installed: $name"
    else
      fail "Skill directory exists but missing SKILL.md: $name"
    fi
  else
    fail "Skill not found: $name (expected at $path)"
    if [[ "$FIX" == true && -d "$REPO_ROOT/skills/$subpath" ]]; then
      mkdir -p "$HERMES_HOME/skills/$(dirname "$subpath")"
      cp -r "$REPO_ROOT/skills/$subpath" "$HERMES_HOME/skills/$subpath"
      ok "[FIX] Re-installed: $name"
    fi
  fi
}

check_skill "department-scrum"
check_skill "brain-ingest-pipeline"
check_skill "brain-first-lookup"
check_skill "brain-e2e-tests"
check_skill "brain-file-delivery"
check_skill "brain-link-campaign"
check_skill "gbrain-capture"
check_skill "gbrain-query"
check_skill "gbrain-think"
check_skill "gbrain-maintain"
check_skill "gbrain-frontmatter-guard"
check_skill "gbrain-signal-detector"
check_skill "timeline-inject-v2"
check_skill "coding-workflow"
check_skill "systematic-debugging"
check_skill "writing-plans"
check_skill "plan"
check_skill "verify-first"
check_skill "search-router"
check_skill "company-workflow"
check_skill "shogunify"
check_skill "customer-communication-onboarding" "crm/customer-communication-onboarding"
check_skill "respondio-bridge" "crm/respondio-bridge"
check_skill "chatwoot-bridge" "crm/chatwoot-bridge"

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
      if "$PYTHON" -c "import py_compile; py_compile.compile(r'$HERMES_HOME_WIN/scripts/$name', doraise=True)" 2>/dev/null; then
        ok "  └─ Syntax check passed: $name"
      else
        fail "  └─ Syntax error in: $name"
      fi
    fi
  else
    fail "Script not found: $path"
    if [[ "$FIX" == true ]]; then
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
check_script "init-gbrain.sh"
check_script "wire-crons.py"
check_script "verify-install.sh"
check_script "verify-comprehensive.py"

echo ""

# ── 3. Configs ───────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Configs ━━━${NC}"

if [[ -f "$HERMES_HOME/config/gmail-batches.json" ]]; then
  ok "Gmail batch config installed"
  # Validate JSON (use Python — jq is often absent on Windows)
  if "$PYTHON" -m json.tool "$HERMES_HOME_WIN/config/gmail-batches.json" > /dev/null 2>&1; then
    ok "  └─ Valid JSON"
  else
    fail "  └─ Invalid JSON"
  fi
else
  # Google DWD ingest is optional (skipped when no service-account key is present)
  warn "Gmail batch config not found: $HERMES_HOME/config/gmail-batches.json (optional — set up Google DWD to enable)"
fi

echo ""

# ── 4. Symlinks ──────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Symlinks ━━━${NC}"

if [[ -L "$HERMES_HOME/service-account-key.json" ]]; then
  target="$(readlink "$HERMES_HOME/service-account-key.json")"
  if [[ -f "$target" ]]; then
    ok "SA-DWD symlink: $HERMES_HOME/service-account-key.json → $target"
  else
    warn "SA-DWD symlink exists but target missing: $target"
  fi
elif [[ -f "$HERMES_HOME/service-account-key.json" ]]; then
  warn "SA-DWD key exists but is a regular file (copy fallback is acceptable on Windows without symlink rights)"
else
  warn "SA-DWD key not found — optional; create ~/.hermes/secrets/google-dwd-sa.json to enable Google DWD ingest"
fi

echo ""

# ── 5. Hermes Health ────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Hermes Health ━━━${NC}"

if command -v hermes &> /dev/null; then
  ok "Hermes CLI available: $(hermes --version 2>&1 | head -1)"

  # Check skills are recognized by Hermes
  if [[ "$QUICK" != true ]]; then
    skills_output=$(hermes skills list 2>&1 || true)
    for skill in "department-scrum" "brain-ingest-pipeline" "brain-compliance" "profile-enrichment" "gbrain-operations"; do
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

    # Live MCP connection test (works without a running gateway)
    if [[ "$QUICK" != true ]]; then
      gbrain_test=$(hermes -p default mcp test gbrain 2>&1 || true)
      if echo "$gbrain_test" | grep -qi "connected\|successful"; then
        ok "  └─ gbrain MCP connects"
      else
        warn "  └─ gbrain MCP configured (live query skipped — gateway may not be running)"
      fi
    fi
  else
    warn "GBrain MCP server not configured for default profile — run 'gbrain serve' and add it via 'hermes -p <profile> mcp add'"
  fi

  # Check stock-scanner MCP (optional)
  if hermes mcp list 2>&1 | grep -qi "stock-scanner"; then
    ok "stock-scanner MCP server is configured"
    if [[ "$QUICK" != true ]]; then
      stock_test=$(hermes -p default mcp test stock-scanner 2>&1 || true)
      if echo "$stock_test" | grep -qi "connected\|successful"; then
        ok "  └─ stock-scanner MCP connects"
      else
        warn "  └─ stock-scanner MCP configured (live query skipped)"
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

# ── Provider abstraction directories ──
echo -e "${CYAN}━━━ Provider Abstraction Recipes ━━━${NC}"

check_abstraction() {
  local name="$1"
  local path="$REPO_ROOT/recipes/$1"
  if [[ -d "$path" ]]; then
    if [[ -f "$path/CONTRACT.md" && -f "$path/GENERIC_SKILL.md" ]]; then
      ok "Abstraction: $name"
    else
      warn "Abstraction directory exists but missing CONTRACT.md or GENERIC_SKILL.md: $name"
    fi
  else
    fail "Abstraction not found: $name"
  fi
}

check_abstraction "hr/time-tracking"
check_abstraction "accounting"
check_abstraction "procurement"
check_abstraction "crm"
check_abstraction "marketing"
check_abstraction "compliance"
check_abstraction "support"
check_abstraction "engineering"
check_abstraction "projects"
check_abstraction "product"

if [[ -d "$REPO_ROOT/docs" ]]; then
  ok "docs/ directory present"
else
  warn "docs/ directory missing"
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

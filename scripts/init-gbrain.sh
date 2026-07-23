#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Shogun OS — GBrain Initialization Script
# ──────────────────────────────────────────────────────────────────────────
# Initializes gbrain and creates all 10 department sources.
# Uses the latest stable gbrain CLI (v0.42.x+ recommended).
#
# Usage:
#   ./scripts/init-gbrain.sh                    # Interactive (prompts before each step)
#   ./scripts/init-gbrain.sh --yes              # Non-interactive, auto-confirm
#   ./scripts/init-gbrain.sh --dry-run          # Preview without changes
#   ./scripts/init-gbrain.sh --help             # Show help
#   ./scripts/init-gbrain.sh --version          # Check gbrain version only
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

VERSION="1.0.0"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
BRAIN_DIR="${BRAIN_DIR:-$HOME/brain}"
GBRAIN_SOURCE="${GBRAIN_SOURCE:-default}"

AUTO=false
DRY_RUN=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()    { echo -e "  ${GREEN}✅${NC} $1"; }
info()  { echo -e "  ${CYAN}💡${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠️${NC} $1"; }
err()   { echo -e "  ${RED}❌${NC} $1"; }

usage() {
  cat <<EOF
Shogun OS — GBrain Initialization Script v${VERSION}

Initializes gbrain and creates all department sources.

USAGE:
  ./scripts/init-gbrain.sh            Interactive (prompts before each step)
  ./scripts/init-gbrain.sh --yes      Non-interactive, auto-confirm
  ./scripts/init-gbrain.sh --dry-run  Preview without changes
  ./scripts/init-gbrain.sh --version  Check gbrain version only
  ./scripts/init-gbrain.sh --help     This message

DEPARTMENT SOURCES:
  shared        - Federated read (staff directory, policies, taxonomy)
  hr            - HR operations, leave, recruitment
  finance       - Budgets, revenue, expenses, reporting
  projects      - Project delivery, milestones, support tickets
  procurement   - POs, vendors, contracts, assets
  products      - PRDs, roadmaps, epics, releases
  crm           - Deals, companies, contacts, activities
  marketing     - Campaigns, content, events, brand
  compliance    - Policies, audits, controls, risk
  engineering   - Codebases, ADRs, quality metrics, deployments
  support       - Tickets, KB articles, customer profiles
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y)    AUTO=true; shift ;;
    --dry-run)   DRY_RUN=true; shift ;;
    --version)   CHECK_VERSION=true; shift ;;
    --help|-h)   usage ;;
    *) err "Unknown option: $1"; echo "  Use --help for usage"; exit 1 ;;
  esac
done

# ── Version Check ──────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Shogun OS — GBrain Init v${VERSION}${NC}"
[[ "$DRY_RUN" == true ]] && echo -e "${YELLOW}  ⚡ DRY RUN — no changes will be made${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

if ! command -v gbrain &> /dev/null; then
  err "gbrain CLI not found in PATH"
  info "Install gbrain (latest stable):"
  info "  bun install -g github:garrytan/gbrain"
  info ""
  info "Or if you don't have bun:"
  info "  curl -fsSL https://bun.sh/install | bash"
  info "  bun install -g github:garrytan/gbrain"
  exit 1
fi

GBRAIN_VERSION=$(gbrain --version 2>&1 | head -1)
ok "gbrain found: $GBRAIN_VERSION"

# Extract major.minor version
VER_MAJOR=$(echo "$GBRAIN_VERSION" | grep -oP 'v?\K[\d]+' | head -1 || echo "0")
VER_MINOR=$(echo "$GBRAIN_VERSION" | grep -oP 'v?[\d]+\.\K[\d]+' | head -1 || echo "0")

if [[ "$VER_MAJOR" -eq 0 && "$VER_MINOR" -lt 42 ]]; then
  warn "gbrain $GBRAIN_VERSION is older than the recommended v0.42.x"
  info "Update:  bun install -g github:garrytan/gbrain"
fi

# If only checking version, exit now
if [[ "${CHECK_VERSION:-false}" == true ]]; then exit 0; fi

# ── Sources to create ──────────────────────────────────────────────────

SOURCES=(
  "shared:Federated read source (staff directory, policies)"
  "hr:HR operations, leave, recruitment"
  "finance:Budgets, revenue, expenses"
  "projects:Project delivery, milestones"
  "procurement:POs, vendors, contracts"
  "products:PRDs, roadmaps, releases"
  "crm:Deals, companies, contacts"
  "marketing:Campaigns, content, brand"
  "compliance:Policies, audits, controls"
  "engineering:Codebases, ADRs, deployments"
  "support:Tickets, KB articles, customers"
)

# ── Confirm ─────────────────────────────────────────────────────────────

if [[ "$AUTO" != true && "$DRY_RUN" != true ]]; then
  echo ""
  echo -e "${YELLOW}This will initialize gbrain and create ${#SOURCES[@]} sources."
  echo -e "Each source gets its own folder under ${BRAIN_DIR}/${NC}"
  echo ""
  read -r -p "Continue? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    info "Aborted by user"
    exit 0
  fi
  echo ""
fi

# ── Initialize gbrain ─────────────────────────────────────────────────

if [[ "$DRY_RUN" == true ]]; then
  ok "[DRY-RUN] Would run: gbrain init"
else
  if [[ -f "$BRAIN_DIR/.gbrain" ]]; then
    ok "gbrain already initialized at $BRAIN_DIR"
  else
    info "Initializing gbrain..."
    gbrain init --dir "$BRAIN_DIR" 2>&1 || warn "gbrain init may have already been run"
    ok "gbrain initialized at $BRAIN_DIR"
  fi
fi

# ── Create sources ───────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Creating Sources ━━━${NC}"

for source_entry in "${SOURCES[@]}"; do
  IFS=':' read -r source_name source_desc <<< "$source_entry"

  source_dir="$BRAIN_DIR/$source_name"
  init_cmd="init-source $source_name"

  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would create source: $source_name → $source_dir"
    continue
  fi

  # Create source directory if it doesn't exist
  if [[ ! -d "$source_dir" ]]; then
    mkdir -p "$source_dir"
    info "Created directory: $source_dir"
  fi

  # Initialize gbrain source
  if gbrain sources list 2>/dev/null | grep -q "id: $source_name"; then
    ok "Source already exists: $source_name"
  else
    # 'gbrain sources add' requires each path to be a git repo
    if [ ! -d "$source_dir/.git" ]; then
      cd "$source_dir" && git init -q && git commit --allow-empty -q -m "init"
    fi
    if gbrain sources add "$source_name" --path "$source_dir" 2>&1; then
      ok "Created source: $source_name ($source_desc)"
    else
      warn "Failed to create source: $source_name"
    fi
  fi
done

# ── Configure federated read ──────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Federated Read Configuration ━━━${NC}"

if [[ "$DRY_RUN" == true ]]; then
  ok "[DRY-RUN] Would enable federated read for all non-shared sources"
else
  # Enable federated read globally
  export GBRAIN_FEDERATED_READ=true
  info "GBRAIN_FEDERATED_READ=true set (add to profile .env or config.yaml)"

  ok "Federated read configured — every profile can read shared/ source"
fi

# ── Verify ─────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Verification ━━━${NC}"

if [[ "$DRY_RUN" != true ]]; then
  if command -v gbrain &> /dev/null; then
    local count
    count=$(gbrain sources list 2>/dev/null | grep -c "id:") || count="?"
    ok "gbrain sources: $count"
    gbrain doctor 2>&1 | head -5 || true
  fi
fi

# ── Summary ────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
if [[ "$DRY_RUN" == true ]]; then
  echo -e "${YELLOW}  ⚡ DRY RUN — No changes made${NC}"
fi
echo -e "${GREEN}  GBrain Init Complete${NC}"
echo -e "    Sources:  ${#SOURCES[@]} department sources"
echo -e "    Brain:    ${BRAIN_DIR}/{shared,hr,finance,...}/"
echo ""
echo -e "${GREEN}  Next Steps:${NC}"
echo -e "    1. Deploy profiles:  ${CYAN}./install.sh --deploy${NC}"
echo -e "    2. Set up Slack bots: ${CYAN}see SETUP.md Phase 4${NC}"
echo -e "    3. Wire crons:        ${CYAN}python3 scripts/wire-crons.py <profile> --apply${NC}"
echo ""
echo -e "  Profile.env config (add to each profile's .env):"
echo -e "    ${CYAN}export GBRAIN_FEDERATED_READ=true${NC}"
echo -e "    ${CYAN}export SUPABASE_URL=...${NC}"
echo -e "    ${CYAN}export SUPABASE_SERVICE_ROLE_KEY=...${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
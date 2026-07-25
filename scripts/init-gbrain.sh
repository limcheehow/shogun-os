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

VERSION="1.2.0"

# Resolve Python interpreter (python3 absent/unusable on Windows)
if command -v python >/dev/null 2>&1 && python -c 'import sys' >/dev/null 2>&1; then
  PYTHON=python
elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
  PYTHON=python3
elif command -v py >/dev/null 2>&1; then
  PYTHON="py -3"
else
  PYTHON=python
fi

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

# Resolve gbrain path (bun global install may not be on the non-interactive PATH)
if command -v gbrain &> /dev/null; then
  GBRAIN_BIN="gbrain"
else
  for cand in "$HOME/.bun/bin/gbrain" "$HOME/.bun/bin/gbrain.exe" "/usr/local/bin/gbrain"; do
    if [[ -x "$cand" ]]; then
      GBRAIN_BIN="$cand"
      break
    fi
  done
fi

if [[ -z "${GBRAIN_BIN:-}" ]]; then
  err "gbrain CLI not found in PATH or common install locations"
  info "Install gbrain (latest stable):"
  info "  bun install -g github:garrytan/gbrain"
  info ""
  info "Or if you don't have bun:"
  info "  curl -fsSL https://bun.sh/install | bash"
  info "  bun install -g github:garrytan/gbrain"
  exit 1
fi

GBRAIN_VERSION=$("$GBRAIN_BIN" --version 2>&1 | head -1)
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

# ── PostgreSQL Setup ────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ PostgreSQL Setup ━━━${NC}"

if command -v psql &> /dev/null; then
  PSQL_VERSION=$(psql --version 2>&1 | head -1)
  ok "PostgreSQL already installed: $PSQL_VERSION"
else
  info "PostgreSQL not found — installing postgresql-16 and postgresql-contrib-16..."
  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would run: sudo apt-get install -y postgresql-16 postgresql-contrib-16"
  else
    sudo apt-get update -qq && sudo apt-get install -y postgresql-16 postgresql-contrib-16 || {
      err "Failed to install PostgreSQL 16"
      exit 1
    }
    ok "PostgreSQL 16 installed"
  fi
fi

# Enable and start PostgreSQL service
if [[ "$DRY_RUN" == true ]]; then
  ok "[DRY-RUN] Would enable + start postgresql service"
else
  sudo systemctl enable postgresql 2>/dev/null || true
  sudo systemctl start postgresql 2>/dev/null || true
  if pg_isready &>/dev/null; then
    ok "PostgreSQL service is running"
  else
    err "PostgreSQL service failed to start"
    exit 1
  fi
fi

# Create gbrain database user (password: 'gbrain') if not exists
if [[ "$DRY_RUN" == true ]]; then
  ok "[DRY-RUN] Would create gbrain database user if not exists"
else
  USER_EXISTS=$(sudo -u postgres psql -t -c "SELECT 1 FROM pg_roles WHERE rolname='gbrain';" 2>/dev/null | tr -d ' ')
  if [[ "$USER_EXISTS" == "1" ]]; then
    ok "gbrain database user already exists"
  else
    sudo -u postgres psql -c "CREATE USER gbrain WITH PASSWORD 'gbrain';" 2>&1 || {
      err "Failed to create gbrain database user"
      exit 1
    }
    ok "Created gbrain database user"
  fi
fi

# Create gbrain database owned by gbrain user if not exists
if [[ "$DRY_RUN" == true ]]; then
  ok "[DRY-RUN] Would create gbrain database owned by gbrain user if not exists"
else
  DB_EXISTS=$(sudo -u postgres psql -t -c "SELECT 1 FROM pg_database WHERE datname='gbrain';" 2>/dev/null | tr -d ' ')
  if [[ "$DB_EXISTS" == "1" ]]; then
    ok "gbrain database already exists"
  else
    sudo -u postgres psql -c "CREATE DATABASE gbrain OWNER gbrain;" 2>&1 || {
      err "Failed to create gbrain database"
      exit 1
    }
    ok "Created gbrain database owned by gbrain"
  fi
fi

# Enable pgvector extension
if [[ "$DRY_RUN" == true ]]; then
  ok "[DRY-RUN] Would enable pgvector extension in gbrain database"
else
  sudo -u postgres psql -d gbrain -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1 || {
    warn "Failed to enable pgvector extension (may not be installed)"
  }
  ok "pgvector extension enabled in gbrain database"
fi

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
    "$GBRAIN_BIN" init --dir "$BRAIN_DIR" 2>&1 || warn "gbrain init may have already been run"
    ok "gbrain initialized at $BRAIN_DIR"
  fi
fi

# ── Create sources ───────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Creating Sources ━━━${NC}"

for source_entry in "${SOURCES[@]}"; do
  IFS=':' read -r source_name source_desc <<< "$source_entry"

  source_dir="$BRAIN_DIR/$source_name"

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
  if "$GBRAIN_BIN" sources list --json 2>/dev/null | grep -q "\"id\": \"$source_name\""; then
    ok "Source already exists: $source_name"
  else
    # 'gbrain sources add' requires a git repo with at least one committed,
    # tracked file (an empty commit no longer qualifies in gbrain v0.42.x).
    # Use a temporary identity so commit works even if git user.* is unset.
    if [ ! -d "$source_dir/.git" ]; then
      git -C "$source_dir" init -q
    fi
    if ! git -C "$source_dir" ls-tree -r --name-only HEAD 2>/dev/null | grep -q .; then
      printf '# %s\n\n%s\n' "$source_name" "$source_desc" > "$source_dir/README.md"
      git -C "$source_dir" -c user.name="Shogun OS Installer" -c user.email="installer@localhost" add README.md
      git -C "$source_dir" -c user.name="Shogun OS Installer" -c user.email="installer@localhost" commit -q -m "init"
    fi
    if "$GBRAIN_BIN" sources add "$source_name" --path "$source_dir" 2>&1; then
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
  ok "[DRY-RUN] Would federate shared and isolate default"
else
  if "$GBRAIN_BIN" sources federate shared 2>&1; then
    ok "Shared source is federated for cross-source reads"
  else
    err "Failed to federate shared source"
    exit 1
  fi

  if "$GBRAIN_BIN" sources unfederate default 2>&1; then
    ok "Legacy default source isolated from department searches"
  else
    warn "Could not isolate default source (it may not exist)"
  fi
fi

# ── Model Tier Configuration ──────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Model Tier Configuration ━━━${NC}"

# Read Hermes default model and resolve a gbrain-compatible model string.
# gbrain's internal tier defaults (anthropic:claude-sonnet-4-6) consume
# a separate ANTHROPIC_API_KEY. Instead, inherit the user's default model
# so gbrain uses the same API key and provider as Hermes.
#
# Provider resolution logic:
#   - If the Hermes provider is a known gbrain provider (openrouter,
#     anthropic, openai, google), pass it through as-is.
#   - If the provider is "custom" (DashScope etc.), use the first
#     fallback provider's model instead — it's routed through a known
#     provider (typically openrouter) and shares the same API key.
#   - If nothing resolves, leave gbrain's built-in defaults untouched.

GBRAIN_MODEL=""

if [[ "$DRY_RUN" != true ]]; then
  GBRAIN_MODEL=$("$PYTHON" -c "
import sys, yaml, os

hermes_home = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))
config_path = os.path.join(hermes_home, 'config.yaml')

if not os.path.exists(config_path):
    sys.exit(0)

with open(config_path) as f:
    cfg = yaml.safe_load(f) or {}

model_cfg = cfg.get('model', {})
provider = (model_cfg.get('provider') or '').strip()
model_name = (model_cfg.get('default') or '').strip()

KNOWN_PROVIDERS = {'openrouter', 'anthropic', 'openai', 'google', 'deepseek', 'mistral', 'groq'}

if provider and model_name:
    if provider in KNOWN_PROVIDERS:
        result = f'{provider}:{model_name}'
    else:
        # Custom provider — use the fallback model instead
        fallbacks = cfg.get('fallback_providers', [])
        for fb in (fallbacks if isinstance(fallbacks, list) else []):
            fb_provider = (fb.get('provider') or '').strip()
            fb_model = (fb.get('model') or '').strip()
            if fb_provider in KNOWN_PROVIDERS and fb_model:
                result = f'{fb_provider}:{fb_model}'
                break
        else:
            # Last resort: emit the model name alone, let gbrain resolve it
            result = model_name
    print(result)
" 2>/dev/null || echo "")
fi

if [[ -n "$GBRAIN_MODEL" ]]; then
  # Check if gbrain already has a custom tier config (user may have set one)
  EXISTING_REASONING=$("$GBRAIN_BIN" config show 2>/dev/null | "$PYTHON" -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('models', {}).get('tier', {}).get('reasoning', ''))
except:
    print('')
" 2>/dev/null || echo "")

  if [[ -n "$EXISTING_REASONING" ]]; then
    info "GBrain tier.reasoning already set: $EXISTING_REASONING (keeping)"
  else
    if [[ "$DRY_RUN" == true ]]; then
      ok "[DRY-RUN] Would set gbrain tier.reasoning = $GBRAIN_MODEL"
    else
      for tier in reasoning utility subagent; do
        if "$GBRAIN_BIN" config set "models.tier.$tier" "$GBRAIN_MODEL" 2>&1; then
          ok "GBrain tier.$tier → $GBRAIN_MODEL"
        else
          warn "Failed to set models.tier.$tier"
        fi
      done
    fi
  fi
else
  info "Using gbrain built-in tier defaults (no Hermes model found to inherit)"
fi

# ── Ollama + Local Embedding ──────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Ollama + Local Embedding ━━━${NC}"

OLLAMA_FOUND=false
if command -v ollama &> /dev/null; then
  OLLAMA_FOUND=true
  OLLAMA_VER=$(ollama --version 2>&1 | head -1)
  ok "Ollama found: $OLLAMA_VER"

  if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    ok "nomic-embed-text model already pulled"
  else
    if [[ "$DRY_RUN" == true ]]; then
      ok "[DRY-RUN] Would pull nomic-embed-text model: ollama pull nomic-embed-text"
    else
      info "Pulling nomic-embed-text model (this may take a moment)..."
      if ollama pull nomic-embed-text 2>&1; then
        ok "nomic-embed-text model pulled"
      else
        err "Failed to pull nomic-embed-text model"
      fi
    fi
  fi
else
  warn "Ollama not found — local embedding will not be available"
  info "Install Ollama:  curl -fsSL https://ollama.com/install.sh | sh"
fi

# ── Schema Pack ────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Schema Pack ━━━${NC}"

SCHEMA_PACK_PATH="$HOME/.gbrain/schema-packs/shogun-enterprise/pack.yaml"
SCHEMA_PACK_FOUND=false
if [[ -f "$SCHEMA_PACK_PATH" ]]; then
  SCHEMA_PACK_FOUND=true
  ok "Schema pack found: shogun-enterprise"
  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would run: gbrain schema use shogun-enterprise"
  else
    if "$GBRAIN_BIN" schema use shogun-enterprise 2>&1; then
      ok "Activated schema pack: shogun-enterprise"
    else
      err "Failed to activate schema pack: shogun-enterprise"
    fi
  fi
else
  info "Schema pack not found at $SCHEMA_PACK_PATH"
  info "It can be created later with:  gbrain schema pack create shogun-enterprise"
fi

# ── Cron Setup ─────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Cron Setup ━━━${NC}"

CRON_INSTALLED=0
EXISTING_CRON=$(crontab -l 2>/dev/null || echo "")

if echo "$EXISTING_CRON" | grep -q "gbrain-dream-cron"; then
  ok "Cron entry already exists: gbrain-dream-cron"
else
  CRON_ENTRY="0 2 * * * \$HOME/shogun-os/scripts/gbrain-dream-cron.sh"
  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would add cron: $CRON_ENTRY"
  else
    CRON_INSTALLED=$((CRON_INSTALLED + 1))
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    ok "Added cron: $CRON_ENTRY"
  fi
fi

if echo "$EXISTING_CRON" | grep -q "gbrain-backup"; then
  ok "Cron entry already exists: gbrain-backup"
else
  CRON_ENTRY="30 2 * * * \$HOME/shogun-os/scripts/gbrain-backup.sh"
  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would add cron: $CRON_ENTRY"
  else
    CRON_INSTALLED=$((CRON_INSTALLED + 1))
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    ok "Added cron: $CRON_ENTRY"
  fi
fi

# ── Verify ─────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Verification ━━━${NC}"

if [[ "$DRY_RUN" != true ]]; then
  if [[ -n "${GBRAIN_BIN:-}" ]]; then
    count=$("$GBRAIN_BIN" sources list --json 2>/dev/null | grep -c '"id":') || count="?"
    ok "gbrain sources: $count"
    "$GBRAIN_BIN" doctor 2>&1 | head -5 || true
  fi
fi

# ── Summary ────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
if [[ "$DRY_RUN" == true ]]; then
  echo -e "${YELLOW}  ⚡ DRY RUN — No changes made${NC}"
fi
echo -e "  ${GREEN}  GBrain Init Complete${NC}"
echo -e "    Sources:  ${#SOURCES[@]} department sources"
echo -e "    Brain:    ${BRAIN_DIR}/{shared,hr,finance,...}/"
echo -e "    Model:    ${GBRAIN_MODEL:-built-in defaults} (inherited from Hermes)"
if [[ "$OLLAMA_FOUND" == true ]]; then
  echo -e "    Ollama:   ${GREEN}installed${NC} (nomic-embed-text)"
else
  echo -e "    Ollama:   ${YELLOW}not found${NC}"
fi
if [[ "$SCHEMA_PACK_FOUND" == true ]]; then
  echo -e "    Schema:   shogun-enterprise (activated)"
else
  echo -e "    Schema:   ${YELLOW}not installed${NC}"
fi
echo -e "    Crons:    $CRON_INSTALLED added (dream + backup)"
echo ""
echo -e "${GREEN}  Next Steps:${NC}"
echo -e "    1. Deploy profiles:  ${CYAN}./install.sh --deploy${NC}"
echo -e "    2. Set up Slack bots: ${CYAN}see SETUP.md Phase 4${NC}"
echo -e "    3. Wire crons:        ${CYAN}python scripts/wire-crons.py <profile> --apply${NC}"
echo ""
echo -e "  Profile.env config (add to each profile's .env):"
echo -e "    ${CYAN}export GBRAIN_FEDERATED_READ=true${NC}"
echo -e "    ${CYAN}export SUPABASE_URL=...${NC}"
echo -e "    ${CYAN}export SUPABASE_SERVICE_ROLE_KEY=...${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
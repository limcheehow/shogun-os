#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Company OS — Hermes Companion Installer
# ──────────────────────────────────────────────────────────────────────────
# Installs skills, scripts, templates, and configs into ~/.hermes/
#
# Usage:
#   ./install.sh                    # Full install
#   ./install.sh --dry-run          # Preview only
#   ./install.sh --force            # Overwrite without backup prompt
#   ./install.sh --profile hr       # Install only HR-relevant assets
#   ./install.sh --help             # Show help
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

VERSION="2.0.0"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"

# ── Flags ──────────────────────────────────────────────────────────────
DRY_RUN=false
FORCE=false
PROFILE=""
DEPLOY=""
BACKUP_DIR=""

# ── Color helpers ──────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ok()  { echo -e "  ${GREEN}✅${NC} $1"; }
info(){ echo -e "  ${CYAN}💡${NC} $1"; }
warn(){ echo -e "  ${YELLOW}⚠️${NC} $1"; }
err() { echo -e "  ${RED}❌${NC} $1"; }

# ── Help ───────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Company OS Installer v${VERSION}

Installs skills, scripts, configs, and templates from this repo into ~/.hermes/

USAGE:
  ./install.sh                    Full install
  ./install.sh --dry-run          Preview without making changes
  ./install.sh --force            Overwrite existing files without backup prompt
  ./install.sh --profile <name>   Install assets relevant to one profile
  ./install.sh --deploy <type>    Full deploy: install + generate-profile + wire-crons for all profiles
  ./install.sh --deploy-profile <name>  Deploy a single profile
  ./install.sh --help             This message

EXAMPLES:
  ./install.sh
  ./install.sh --dry-run --profile project-manager
  ./install.sh --force
  ./install.sh --deploy all
  ./install.sh --deploy-profile hr-manager --type hr
EOF
  exit 0
}

# ── Parse args ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --force)   FORCE=true; shift ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --deploy)   DEPLOY="all"; shift ;;
    --deploy-profile) DEPLOY="$2"; shift 2 ;;
    --help|-h) usage ;;
    *) err "Unknown option: $1"; echo "  Use --help for usage"; exit 1 ;;
  esac
done

# ── Validate repo root ─────────────────────────────────────────────────
if [[ ! -d "$REPO_ROOT/skills" ]]; then
  err "Cannot find 'skills/' directory. Run this script from the company-os repo root."
  echo "  Expected: $REPO_ROOT/skills"
  exit 1
fi

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Company OS Installer v${VERSION}${NC}"
echo -e "${CYAN}  Repo: ${REPO_ROOT}${NC}"
if [[ -n "$PROFILE" ]]; then
  echo -e "${CYAN}  Profile: ${PROFILE}${NC}"
fi
if [[ "$DRY_RUN" == true ]]; then
  echo -e "${YELLOW}  ⚡ DRY RUN — no files will be modified${NC}"
fi
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

# ── Backup existing ────────────────────────────────────────────────────
backup_existing() {
  local src="$1"
  if [[ -e "$src" && "$FORCE" != true && "$DRY_RUN" != true ]]; then
    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"
    BACKUP_DIR="$HERMES_HOME/.company-os-backup/$timestamp"
    mkdir -p "$BACKUP_DIR"
    cp -r "$src" "$BACKUP_DIR/" 2>/dev/null || true
    info "Backed up $src → $BACKUP_DIR/"
  fi
}

# ── Install step ───────────────────────────────────────────────────────
install_file() {
  local src="$1"
  local dst="$2"
  local label="${3:-}"

  if [[ ! -e "$src" ]]; then
    warn "Source missing: $src"
    return
  fi

  if [[ -e "$dst" ]]; then
    if [[ "$FORCE" != true && "$DRY_RUN" != true ]]; then
      warn "Already exists: $dst (use --force to overwrite)"
      return
    fi
    backup_existing "$dst"
  fi

  if [[ "$DRY_RUN" == true ]]; then
    if [[ -n "$label" ]]; then
      ok "[DRY-RUN] Would install $label → $dst"
    else
      ok "[DRY-RUN] Would copy $src → $dst"
    fi
    return
  fi

  mkdir -p "$(dirname "$dst")"
  if [[ -d "$src" ]]; then
    cp -r "$src" "$dst"
  else
    cp "$src" "$dst"
  fi

  if [[ -n "$label" ]]; then
    ok "Installed $label"
  else
    ok "Copied $(basename "$src")"
  fi
}

# ── Count files to install ─────────────────────────────────────────────
COUNT_SKILLS=0
COUNT_SCRIPTS=0
COUNT_CONFIGS=0

count_dir() {
  local dir="$1"
  if [[ -d "$dir" ]]; then
    find "$dir" -type f | wc -l
  else
    echo 0
  fi
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Skills
# ═══════════════════════════════════════════════════════════════════════
section_skills() {
  echo -e "${CYAN}━━━ Skills ━━━${NC}"

  local skills_src="$REPO_ROOT/skills"
  local skills_dst="$HERMES_HOME/skills"

  if [[ -n "$PROFILE" ]]; then
    # Profile-specific: only install the scrum skill (needed by all profiles)
    if [[ -d "$skills_src/department-scrum" ]]; then
      install_file "$skills_src/department-scrum" "$skills_dst/department-scrum" "department-scrum skill"
      COUNT_SKILLS=$((COUNT_SKILLS + 1))
    fi
    # If the profile is "default" or the user explicitly wants pipeline, install it
    if [[ "$PROFILE" == "default" || "$PROFILE" == "pipeline" ]]; then
      if [[ -d "$skills_src/brain-ingest-pipeline" ]]; then
        install_file "$skills_src/brain-ingest-pipeline" "$skills_dst/brain-ingest-pipeline" "brain-ingest-pipeline skill"
        COUNT_SKILLS=$((COUNT_SKILLS + 1))
      fi
    fi
  else
    # Full install: all skills
    for skill_dir in "$skills_src"/*/; do
      local name
      name="$(basename "$skill_dir")"
      local dst="$skills_dst/$name"
      # Remove trailing slash from src
      local src="${skill_dir%/}"
      install_file "$src" "$dst" "$name skill"
      COUNT_SKILLS=$((COUNT_SKILLS + 1))
    done
  fi
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Scripts
# ═══════════════════════════════════════════════════════════════════════
section_scripts() {
  echo -e "${CYAN}━━━ Scripts ━━━${NC}"

  local scripts_dst="$HERMES_HOME/scripts"
  local skills_src="$REPO_ROOT/skills"

  # Copy all scripts from all skill directories flat to ~/.hermes/scripts/
  # Names are unique across skills (send-scrum-dms.py, gmail-triage.py, etc.)
  local script_path
  while IFS= read -r script_path; do
    local filename
    filename="$(basename "$script_path")"
    install_file "$script_path" "$scripts_dst/$filename" "$filename"
    COUNT_SCRIPTS=$((COUNT_SCRIPTS + 1))
  done < <(find "$skills_src" -path '*/scripts/*' -type f)

  # Also copy switch-profile.py
  if [[ -f "$REPO_ROOT/scripts/switch-profile.py" ]]; then
    install_file "$REPO_ROOT/scripts/switch-profile.py" "$scripts_dst/switch-profile.py" "switch-profile.py"
    COUNT_SCRIPTS=$((COUNT_SCRIPTS + 1))
  fi
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Templates & Configs
# ═══════════════════════════════════════════════════════════════════════
section_configs() {
  echo -e "${CYAN}━━━ Configs & Examples ━━━${NC}"

  # Gmail batch config
  if [[ -f "$REPO_ROOT/examples/brain-ingest-configs/gmail-batches.json" ]]; then
    install_file "$REPO_ROOT/examples/brain-ingest-configs/gmail-batches.json" \
      "$HERMES_HOME/config/gmail-batches.json" "gmail batch config"
    COUNT_CONFIGS=$((COUNT_CONFIGS + 1))
  fi

  # Scrum config example (informational only)
  if [[ -f "$REPO_ROOT/examples/scrum-configs/project-manager.yaml" ]]; then
    local scrum_dst="$HERMES_HOME/company-os-examples/scrum-configs"
    install_file "$REPO_ROOT/examples/scrum-configs/project-manager.yaml" \
      "$scrum_dst/project-manager.yaml" "scrum config example"
    COUNT_CONFIGS=$((COUNT_CONFIGS + 1))
  fi
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: SA Key Symlink
# ═══════════════════════════════════════════════════════════════════════
section_symlink() {
  echo -e "${CYAN}━━━ Service Account Symlink ━━━${NC}"

  local sa_target="$HERMES_HOME/secrets/google-dwd-sa.json"
  local sa_link="$HERMES_HOME/service-account-key.json"

  if [[ ! -f "$sa_target" ]]; then
    warn "SA-DWD key not found at $sa_target"
    info "Create one first: see recipes/google-dwd.md"
    info "Then re-run install.sh to create the symlink"
    return
  fi

  if [[ -L "$sa_link" && "$(readlink "$sa_link")" == "$sa_target" ]]; then
    ok "SA key symlink already points correctly"
    return
  fi

  if [[ -e "$sa_link" && "$FORCE" != true && "$DRY_RUN" != true ]]; then
    warn "File exists at $sa_link (not a symlink to $sa_target)"
    info "Use --force to overwrite"
    return
  fi

  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would create: $sa_link → $sa_target"
    return
  fi

  ln -sf "$sa_target" "$sa_link"
  ok "Created symlink: $sa_link → $sa_target"
}

# ═══════════════════════════════════════════════════════════════════════
#  GBRAIN VERSION CHECK
# ═══════════════════════════════════════════════════════════════════════
section_gbrain() {
  echo -e "${CYAN}━━━ GBrain ━━━${NC}"

  if ! command -v gbrain &> /dev/null; then
    warn "gbrain CLI not found in PATH"
    info "Install gbrain:  bun install -g github:garrytan/gbrain"
    info "Or install via curl:  curl -fsSL https://bun.sh/install | bash && bun install -g github:garrytan/gbrain"
    return
  fi

  local version
  version=$(gbrain --version 2>&1 | head -1)
  ok "gbrain installed: $version"

  # Extract version number for comparison
  local ver_num
  ver_num=$(echo "$version" | grep -oP 'v?[\d]+\.[\d]+\.?[\d]*' | head -1)
  if [[ -z "$ver_num" ]]; then
    info "Could not parse gbrain version (expected format: v0.x.y)"
  fi

  info "Recommended: gbrain v0.42.x or later (latest stable)"
  info "If gbrain is outdated, run:  bun install -g github:garrytan/gbrain"
}

# ═══════════════════════════════════════════════════════════════════════
#  DEPLOY ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════
section_deploy() {
  local deploy_target="$1"
  echo -e "${CYAN}━━━ Deploy ━━━${NC}"

  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would deploy profiles"
    return
  fi

  if [[ "$deploy_target" == "all" ]]; then
    # Deploy all 10 department profiles
    local profiles="coding-agent hr-manager finance-manager project-manager procurement-manager product-manager crm-manager marketing-manager compliance-manager customer-support"
    local types="coding hr finance project-manager procurement product crm marketing compliance support"

    local i=0
    local p_arr=($profiles)
    local t_arr=($types)

    info "Deploying ${#p_arr[@]} profiles..."
    for ((i=0; i<${#p_arr[@]}; i++)); do
      local pname="${p_arr[$i]}"
      local ptype="${t_arr[$i]}"

      echo ""
      info "Deploying profile: $pname ($ptype)..."

      # Step 1: Create Hermes profile
      if command -v hermes &> /dev/null; then
        hermes profile create "$pname" 2>/dev/null || warn "Profile $pname may already exist"
      else
        warn "hermes CLI not found — skipping profile creation"
      fi

      # Step 2: Generate profile config
      if [[ -f "$REPO_ROOT/scripts/generate-profile.py" ]]; then
        python3 "$REPO_ROOT/scripts/generate-profile.py" "$pname" --type "$ptype" --force 2>&1 || warn "Profile generation failed for $pname"
      fi
    done

    echo ""
    ok "All profiles deployed"

  elif [[ -n "$deploy_target" ]]; then
    # Deploy single profile — format: profile-name:type
    local pname="$deploy_target"
    local ptype="${2:-base}"

    echo ""
    info "Deploying profile: $pname ($ptype)..."

    if command -v hermes &> /dev/null; then
      hermes profile create "$pname" 2>/dev/null || warn "Profile $pname may already exist"
    fi

    if [[ -f "$REPO_ROOT/scripts/generate-profile.py" ]]; then
      python3 "$REPO_ROOT/scripts/generate-profile.py" "$pname" --type "$ptype" --force 2>&1 || warn "Profile generation failed"
    fi

    info "Next: set up Slack bot and wire crons for $pname"
  fi
}

# ═══════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print_summary() {
  echo ""
  echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}  ⚡ DRY RUN — No changes made${NC}"
    echo ""
  fi
  echo -e "${GREEN}  Summary:${NC}"
  echo -e "    Skills : $COUNT_SKILLS installed"
  echo -e "    Scripts: $COUNT_SCRIPTS installed"
  echo -e "    Configs: $COUNT_CONFIGS installed"
  echo ""
  echo -e "${GREEN}  Next Steps:${NC}"
  echo -e "    1. Set up Google DWD:  ${CYAN}see recipes/google-dwd.md${NC}"
  echo -e "    2. Init gbrain:         ${CYAN}scripts/init-gbrain.sh${NC}"
  echo -e "    3. Deploy profiles:     ${CYAN}./install.sh --deploy all${NC}"
  echo -e "    4. Wire scrum crons:    ${CYAN}python3 scripts/wire-crons.py <profile> --apply${NC}"
  echo -e "    5. Set up Slack bots:   ${CYAN}see SETUP.md Phase 4${NC}"
  echo -e "    6. Verify install:      ${CYAN}./scripts/verify-install.sh${NC}"
  if [[ -n "$BACKUP_DIR" ]]; then
    echo ""
    info "Backups saved to: $BACKUP_DIR"
  fi
  echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
  echo ""
}

# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════
main() {
  section_skills
  echo ""
  section_scripts
  echo ""
  section_configs
  echo ""
  section_gbrain
  echo ""
  section_symlink
  echo ""
  print_summary
  echo ""

  # Deploy mode: install + generate profiles
  if [[ -n "$DEPLOY" ]]; then
    section_deploy "$DEPLOY"
  fi
}

main
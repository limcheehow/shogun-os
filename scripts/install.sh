#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Shogun OS — Hermes Companion Installer v3.1.1
# ──────────────────────────────────────────────────────────────────────────
# Installs skills, scripts, recipes, templates, and configs into ~/.hermes/
#
# Usage:
#   ./install.sh                    # Full install
#   ./install.sh --dry-run          # Preview only
#   ./install.sh --force            # Overwrite without backup prompt
#   ./install.sh --profile hr       # Install only HR-relevant assets
#   ./install.sh --industry general   # Deploy general industry profiles
#   ./install.sh --industry manufacturing  # Deploy manufacturing profiles
#   ./install.sh --deploy           # Install + generate all department profiles (prompts for industry)
#   ./install.sh --deploy-profile hr-manager --type hr  # Deploy one profile
#   ./install.sh --systemd          # Install systemd template units
#   ./install.sh --help             # Show help
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

VERSION="3.9.0"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"

# ── Flags ──────────────────────────────────────────────────────────────
DRY_RUN=false
FORCE=false
PROFILE=""
DEPLOY=""
INDUSTRY=""
INSTALL_SYSTEMD=false
BACKUP_DIR=""

# ── Industry profiles ─────────────────────────────────────────────────
SHARED_PROFILES="coding-agent hr-manager finance-manager procurement-manager crm-manager marketing-manager compliance-manager customer-support"
SHARED_TYPES="coding hr finance procurement crm marketing compliance support"

GENERAL_EXTRA="project-manager product-manager"
GENERAL_EXTRA_TYPES="project-manager product"

MANUFACTURING_EXTRA="production-manager quality-manager maintenance-manager warehouse-manager hse-manager"
MANUFACTURING_EXTRA_TYPES="production quality maintenance warehouse hse"

RETAIL_EXTRA="stores-manager merchandising-manager ecommerce-manager crm-retail-manager supplychain-manager vm-manager"
RETAIL_EXTRA_TYPES="stores merchandising ecommerce crm-retail supplychain vm"

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
Shogun OS Installer v${VERSION}

Installs skills, scripts, recipes, configs, templates, and systemd units
from this repo into ~/.hermes/

USAGE:
  ./install.sh                    Full install
  ./install.sh --dry-run          Preview without making changes
  ./install.sh --force            Overwrite existing files without backup prompt
  ./install.sh --profile <name>   Install assets relevant to one profile
  ./install.sh --deploy           Full deploy: install + generate all profiles (prompts for industry)
  ./install.sh --deploy --industry general    Deploy general industry profiles
  ./install.sh --deploy --industry manufacturing  Deploy manufacturing profiles
  ./install.sh --deploy-profile <name> --type <type>  Deploy a single profile
  ./install.sh --systemd          Install systemd template units for gateway management
  ./install.sh --help             This message

EXAMPLES:
  ./install.sh
  ./install.sh --dry-run --profile project-manager
  ./install.sh --force
  ./install.sh --deploy --industry manufacturing
  ./install.sh --deploy-profile hr-manager --type hr
  ./install.sh --deploy-profile production-manager --type production  # Manufacturing
  ./install.sh --systemd

WHAT GETS INSTALLED:
  Skills    → ~/.hermes/skills/              (All skills)
  Scripts   → ~/.hermes/scripts/             (All scripts)
  Recipes   → ~/.hermes/recipes/             (13 recipes)
  Templates → ~/.hermes/templates/           (3 template files)
  Configs   → ~/.hermes/config/              (gmail batches, scrum examples)
  Systemd   → ~/.config/systemd/user/        (hermes-gateway@.service template)
  SA Symlink→ ~/.hermes/service-account-key.json

NEXT STEPS AFTER INSTALL:
  1. Set up Google DWD:     see recipes/google-dwd.md
  2. Init gbrain:           scripts/init-gbrain.sh --yes
  3. Deploy profiles:       ./install.sh --deploy
  4. Wire scrum crons:      python scripts/wire-crons.py <profile> --apply
  5. Set up Slack bots:     see SETUP.md Phase 4
  6. Install systemd:       ./install.sh --systemd
  7. Verify install:        ./scripts/verify-install.sh
  8. Run tests:             python scripts/verify-comprehensive.py
EOF
  exit 0
}

# ── Parse args ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY_RUN=true; shift ;;
    --force)          FORCE=true; shift ;;
    --profile)        PROFILE="$2"; shift 2 ;;
    --deploy)         DEPLOY="all"; shift ;;
    --deploy-profile) DEPLOY="$2"; shift 2 ;;
    --industry)       INDUSTRY="$2"; shift 2 ;;
    --systemd)        INSTALL_SYSTEMD=true; shift ;;
    --help|-h)        usage ;;
    *) err "Unknown option: $1"; echo "  Use --help for usage"; exit 1 ;;
  esac
done

# ── Validate repo root ─────────────────────────────────────────────────
if [[ ! -d "$REPO_ROOT/skills" ]]; then
  err "Cannot find 'skills/' directory. Run this script from the shogun-os repo root."
  echo "  Expected: $REPO_ROOT/skills"
  exit 1
fi

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Shogun OS Installer v${VERSION}${NC}"
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
    BACKUP_DIR="$HERMES_HOME/.shogun-os-backup/$timestamp"
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

# ── Make executable ────────────────────────────────────────────────────
make_executable() {
  local dst="$1"
  if [[ "$DRY_RUN" != true && -f "$dst" ]]; then
    chmod +x "$dst" 2>/dev/null || true
  fi
}

# ── Count files to install ─────────────────────────────────────────────
COUNT_SKILLS=0
COUNT_SCRIPTS=0
COUNT_RECIPES=0
COUNT_TEMPLATES=0
COUNT_CONFIGS=0
COUNT_SYSTEMD=0

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
    # Profile-specific: install company-workflow + department-scrum (needed by all profiles)
    for required_skill in company-workflow department-scrum; do
      if [[ -d "$skills_src/$required_skill" ]]; then
        install_file "$skills_src/$required_skill" "$skills_dst/$required_skill" "$required_skill skill"
        COUNT_SKILLS=$((COUNT_SKILLS + 1))
      fi
    done
    # If the profile is "default" or "pipeline", install brain-ingest-pipeline
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
      local src="${skill_dir%/}"
      install_file "$src" "$dst" "$name skill"
      COUNT_SKILLS=$((COUNT_SKILLS + 1))
    done
  fi
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Scripts (repo scripts + skill scripts)
# ═══════════════════════════════════════════════════════════════════════
section_scripts() {
  echo -e "${CYAN}━━━ Scripts ━━━${NC}"

  local scripts_dst="$HERMES_HOME/scripts"
  local skills_src="$REPO_ROOT/skills"
  local repo_scripts="$REPO_ROOT/scripts"

  # 1. Copy all repo-level scripts (not install.sh itself, not verify-*.py test files)
  local script_path
  while IFS= read -r script_path; do
    local filename
    filename="$(basename "$script_path")"
    [[ "$filename" == "install.sh" ]] && continue
    install_file "$script_path" "$scripts_dst/$filename" "$filename"
    make_executable "$scripts_dst/$filename"
    COUNT_SCRIPTS=$((COUNT_SCRIPTS + 1))
  done < <(find "$repo_scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) | sort)

  # 2. Copy all scripts from skill directories (flat — names are unique)
  while IFS= read -r script_path; do
    local filename
    filename="$(basename "$script_path")"
    # Skip test files
    [[ "$filename" == test-* ]] && continue
    [[ "$filename" == *_test.py ]] && continue
    # Skip __pycache__
    [[ "$script_path" == *__pycache__* ]] && continue
    install_file "$script_path" "$scripts_dst/$filename" "$filename"
    make_executable "$scripts_dst/$filename"
    COUNT_SCRIPTS=$((COUNT_SCRIPTS + 1))
  done < <(find "$skills_src" -path '*/scripts/*' -type f \( -name '*.sh' -o -name '*.py' \) | sort)
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Recipes
# ═══════════════════════════════════════════════════════════════════════
section_recipes() {
  echo -e "${CYAN}━━━ Recipes ━━━${NC}"

  local recipes_src="$REPO_ROOT/recipes"
  local recipes_dst="$HERMES_HOME/recipes"

  # Copy all .md recipe files
  local recipe_path
  while IFS= read -r recipe_path; do
    local filename
    filename="$(basename "$recipe_path")"
    install_file "$recipe_path" "$recipes_dst/$filename" "$filename"
    COUNT_RECIPES=$((COUNT_RECIPES + 1))
  done < <(find "$recipes_src" -name '*.md' -type f | sort)

  # Copy provider abstraction directories (CONTRACT.md + GENERIC_SKILL.md + bridges + plugins)
  local abstraction_dirs=(
    "hr/time-tracking"
    "accounting"
    "procurement"
    "crm"
    "marketing"
    "compliance"
    "support"
    "engineering"
    "projects"
    "product"
  )
  for dir in "${abstraction_dirs[@]}"; do
    if [[ -d "$recipes_src/$dir" ]]; then
      install_file "$recipes_src/$dir" "$recipes_dst/$dir" "$dir abstraction"
      COUNT_RECIPES=$((COUNT_RECIPES + 1))
    fi
  done
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Templates
# ═══════════════════════════════════════════════════════════════════════
section_templates() {
  echo -e "${CYAN}━━━ Templates ━━━${NC}"

  local templates_src="$REPO_ROOT/templates"
  local templates_dst="$HERMES_HOME/templates"

  # Copy all template files, preserving directory structure
  local tmpl_path
  while IFS= read -r tmpl_path; do
    local rel
    rel="$(realpath --relative-to="$templates_src" "$tmpl_path")"
    install_file "$tmpl_path" "$templates_dst/$rel" "$rel"
    COUNT_TEMPLATES=$((COUNT_TEMPLATES + 1))
  done < <(find "$templates_src" -type f | sort)
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Configs & Examples
# ═══════════════════════════════════════════════════════════════════════
section_configs() {
  echo -e "${CYAN}━━━ Configs & Examples ━━━${NC}"

  # Gmail batch config
  if [[ -f "$REPO_ROOT/examples/brain-ingest-configs/gmail-batches.json" ]]; then
    install_file "$REPO_ROOT/examples/brain-ingest-configs/gmail-batches.json" \
      "$HERMES_HOME/config/gmail-batches.json" "gmail batch config"
    COUNT_CONFIGS=$((COUNT_CONFIGS + 1))
  fi

  # All scrum config examples
  if [[ -d "$REPO_ROOT/examples/scrum-configs" ]]; then
    local scrum_dst="$HERMES_HOME/shogun-os-examples/scrum-configs"
    local scf
    while IFS= read -r scf; do
      local fname
      fname="$(basename "$scf")"
      install_file "$scf" "$scrum_dst/$fname" "scrum config: $fname"
      COUNT_CONFIGS=$((COUNT_CONFIGS + 1))
    done < <(find "$REPO_ROOT/examples/scrum-configs" -name '*.yaml' -type f | sort)
  fi
}

# ═══════════════════════════════════════════════════════════════════════
#  INSTALL: Systemd Template Units
# ═══════════════════════════════════════════════════════════════════════
section_systemd() {
  echo -e "${CYAN}━━━ Systemd Template Unit ━━━${NC}"

  local systemd_dir="$HOME/.config/systemd/user"
  local unit_file="$systemd_dir/hermes-gateway@.service"

  if [[ ! -d "$systemd_dir" ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      ok "[DRY-RUN] Would create $systemd_dir"
    else
      mkdir -p "$systemd_dir"
      ok "Created $systemd_dir"
    fi
  fi

  # Write the template unit file
  local unit_content
  unit_content='[Unit]
Description=Hermes Agent Gateway - %i Profile
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=__HERMES_VENV__/python -m hermes_cli.main --profile %i gateway run
WorkingDirectory=__HERMES_HOME__
Environment="PATH=__HERMES_VENV__:__HERMES_HOME__/node/bin:__LOCAL_BIN__:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="VIRTUAL_ENV=__HERMES_VENV__"
Environment="HERMES_HOME=__HERMES_HOME__"
Restart=always
RestartSec=5
RestartForceExitStatus=75
KillMode=mixed
KillSignal=SIGTERM
ExecStopPost=-__HERMES_VENV__/python -m gateway.cgroup_cleanup
TimeoutStopSec=210
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target'

  # Replace placeholders with actual paths
  local hermes_venv="$HERMES_HOME/hermes-agent/venv"
  local local_bin="$HOME/.local/bin"
  unit_content="${unit_content//__HERMES_VENV__/$hermes_venv}"
  unit_content="${unit_content//__HERMES_HOME__/$HERMES_HOME}"
  unit_content="${unit_content//__LOCAL_BIN__/$local_bin}"

  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would write hermes-gateway@.service to $systemd_dir"
    COUNT_SYSTEMD=$((COUNT_SYSTEMD + 1))
    return
  fi

  # Check if already exists and correct
  if [[ -f "$unit_file" ]]; then
    local existing
    existing=$(cat "$unit_file" 2>/dev/null || echo "")
    if [[ "$existing" == "$unit_content" ]]; then
      ok "hermes-gateway@.service already up to date"
      COUNT_SYSTEMD=$((COUNT_SYSTEMD + 1))
      return
    fi
    backup_existing "$unit_file"
  fi

  echo "$unit_content" > "$unit_file"
  ok "Installed hermes-gateway@.service"
  COUNT_SYSTEMD=$((COUNT_SYSTEMD + 1))

  # Reload systemd
  systemctl --user daemon-reload 2>/dev/null || true
  ok "Systemd daemon reloaded"

  # Check lingering
  if command -v loginctl &> /dev/null; then
    local linger
    linger=$(loginctl show-user "$USER" 2>/dev/null | grep "^Linger=" | cut -d= -f2 || echo "no")
    if [[ "$linger" != "yes" ]]; then
      warn "Lingering is not enabled — user services will die when you log out"
      info "Enable with:  sudo loginctl enable-linger $USER"
    else
      ok "Lingering is enabled"
    fi
  fi

  # Install restart-profile-gateway.sh if not already there
  local restart_script="$HERMES_HOME/scripts/restart-profile-gateway.sh"
  if [[ ! -f "$restart_script" && -f "$REPO_ROOT/scripts/restart-profile-gateway.sh" ]]; then
    install_file "$REPO_ROOT/scripts/restart-profile-gateway.sh" "$restart_script" "restart-profile-gateway.sh"
    make_executable "$restart_script"
  fi

  # Create symlinks for each profile that has a directory
  if [[ -d "$HERMES_HOME/profiles" ]]; then
    local profile_dir
    for profile_dir in "$HERMES_HOME/profiles"/*/; do
      [[ -d "$profile_dir" ]] || continue
      local pname
      pname="$(basename "$profile_dir")"
      local scripts_dir="$profile_dir/scripts"
      local link_path="$scripts_dir/restart-gateway.sh"

      if [[ "$DRY_RUN" == true ]]; then
        ok "[DRY-RUN] Would symlink restart-gateway.sh for $pname"
        continue
      fi

      mkdir -p "$scripts_dir" 2>/dev/null || true
      if [[ ! -L "$link_path" ]]; then
        ln -sf "$restart_script" "$link_path" 2>/dev/null || true
        ok "Symlinked restart-gateway.sh for $pname"
      fi
    done
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
    # Ask about industry
    if [[ -z "$INDUSTRY" ]]; then
      echo ""
      info "Select your industry:"
      echo "    1) General (services, consulting, software)"
      echo "    2) Manufacturing (factory, production, OEM)"
      echo "    3) Retail (stores, e-commerce, omnichannel)"
      read -p "    Choice [1]: " INDUSTRY
      INDUSTRY=${INDUSTRY:-1}
    fi

    # Deploy shared profiles (every industry)
    local profiles="$SHARED_PROFILES"
    local types="$SHARED_TYPES"

    # Add industry-specific profiles
    if [[ "$INDUSTRY" == "2" ]]; then
      profiles="$profiles $MANUFACTURING_EXTRA"
      types="$types $MANUFACTURING_EXTRA_TYPES"
      info "Manufacturing profiles included: production, quality, maintenance, warehouse, HSE"
    elif [[ "$INDUSTRY" == "3" ]]; then
      profiles="$profiles $RETAIL_EXTRA"
      types="$types $RETAIL_EXTRA_TYPES"
      info "Retail profiles included: stores, merchandising, e-commerce, CRM-retail, supply chain, VM"
    else
      profiles="$profiles $GENERAL_EXTRA"
      types="$types $GENERAL_EXTRA_TYPES"
      info "General profiles included: project-manager, product-manager"
    fi

    local i=0
    local p_arr=($profiles)
    local t_arr=($types)

    local deploy_ok=0
    local deploy_fail=0

    info "Deploying ${#p_arr[@]} profiles..."
    for ((i=0; i<${#p_arr[@]}; i++)); do
      local pname="${p_arr[$i]}"
      local ptype="${t_arr[$i]}"

      echo ""
      info "Deploying profile: $pname ($ptype)..."

      # Step 1: Create Hermes profile (treat a real failure as fatal, not "already exists")
      if command -v hermes &> /dev/null; then
        if hermes profile show "$pname" >/dev/null 2>&1; then
          info "Profile $pname already exists — keeping"
        elif hermes profile create "$pname" 2>/dev/null; then
          ok "Created Hermes profile: $pname"
        else
          err "Profile creation failed for $pname — aborting deploy"
          deploy_fail=$((deploy_fail + 1))
          continue
        fi
      else
        warn "hermes CLI not found — skipping profile creation"
      fi

      # Step 2: Generate profile config
      if [[ -f "$REPO_ROOT/scripts/generate-profile.py" ]]; then
        if python "$REPO_ROOT/scripts/generate-profile.py" "$pname" --type "$ptype" --force 2>&1; then
          deploy_ok=$((deploy_ok + 1))
        else
          err "Profile generation failed for $pname"
          deploy_fail=$((deploy_fail + 1))
        fi
      fi
    done

    echo ""
    if [[ "$deploy_fail" -gt 0 ]]; then
      err "$deploy_fail profile(s) failed, $deploy_ok succeeded"
    else
      ok "All profiles deployed ($deploy_ok)"
    fi

  elif [[ -n "$deploy_target" ]]; then
    # Deploy single profile — format: profile-name:type
    local pname="$deploy_target"
    local ptype="${2:-base}"

    echo ""
    info "Deploying profile: $pname ($ptype)..."

    if command -v hermes &> /dev/null; then
      if hermes profile show "$pname" >/dev/null 2>&1; then
        info "Profile $pname already exists — keeping"
      elif hermes profile create "$pname" 2>/dev/null; then
        ok "Created Hermes profile: $pname"
      else
        err "Profile creation failed for $pname"
        return 1
      fi
    fi

    if [[ -f "$REPO_ROOT/scripts/generate-profile.py" ]]; then
      python "$REPO_ROOT/scripts/generate-profile.py" "$pname" --type "$ptype" --force 2>&1 || err "Profile generation failed for $pname"
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
  echo -e "    Skills    : $COUNT_SKILLS installed"
  echo -e "    Scripts   : $COUNT_SCRIPTS installed"
  echo -e "    Recipes   : $COUNT_RECIPES installed"
  echo -e "    Templates : $COUNT_TEMPLATES installed"
  echo -e "    Configs   : $COUNT_CONFIGS installed"
  echo -e "    Systemd   : $COUNT_SYSTEMD installed"
  echo ""
  echo -e "${GREEN}  Next Steps:${NC}"
  echo -e "    1. Set up Google DWD:  ${CYAN}see recipes/google-dwd.md${NC}"
  echo -e "    2. Init gbrain:         ${CYAN}scripts/init-gbrain.sh --yes${NC}"
  echo -e "    3. Deploy profiles:     ${CYAN}./install.sh --deploy${NC}"
  echo -e "    4. Wire scrum crons:    ${CYAN}python scripts/wire-crons.py <profile> --apply${NC}"
  echo -e "    5. Set up Slack bots:   ${CYAN}see SETUP.md Phase 4${NC}"
  echo -e "    6. Install systemd:     ${CYAN}./install.sh --systemd${NC}"
  echo -e "    7. Verify install:      ${CYAN}./scripts/verify-install.sh${NC}"
  echo -e "    8. Run tests:           ${CYAN}python scripts/verify-comprehensive.py${NC}"
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
  section_recipes
  echo ""
  section_templates
  echo ""
  section_configs
  echo ""
  section_gbrain
  echo ""
  section_symlink
  echo ""

  # Systemd (only if --systemd flag or --deploy)
  if [[ "$INSTALL_SYSTEMD" == true ]]; then
    section_systemd
    echo ""
  fi

  print_summary
  echo ""

  # Deploy mode: install + generate profiles
  if [[ -n "$DEPLOY" ]]; then
    section_deploy "$DEPLOY"
  fi
}

main

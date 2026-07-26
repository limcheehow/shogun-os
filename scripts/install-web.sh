#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Shogun OS — Web Portal Installer
# ──────────────────────────────────────────────────────────────────────────
# Sets up shogun-web (FastAPI + React), tenant config, registry registration,
# and systemd user services for the portal + department Hermes gateways.
#
# Product design:
#   - ONE company dashboard for ALL department agents (not per-dept portals)
#   - URL is assigned centrally by OUR registry/Cloudflare (random slug)
#   - Customers never need a Cloudflare account or pick a subdomain
#
# Usage:
#   ./scripts/install-web.sh
#   ./scripts/install-web.sh --admin-email admin@acme.com
#   ./scripts/install-web.sh --dry-run
#   ./scripts/install-web.sh --skip-registry --skip-systemd
#   ./scripts/install-web.sh --help
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

VERSION="0.3.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$SCRIPT_DIR/.." && pwd)")"
SHOGUN_WEB_DIR="${SHOGUN_WEB_DIR:-$REPO_ROOT/shogun-web}"
SHOGUN_HOME="${SHOGUN_HOME:-$HOME/.shogun-os}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
TEMPLATE_DIR="$REPO_ROOT/templates/web-portal"

# Defaults (overridable via flags / env)
# SUBDOMAIN is assigned by central registry after register. Local placeholder
# until then; do NOT ask the customer to choose one.
SUBDOMAIN="${SHOGUN_SUBDOMAIN:-}"
VANITY_SUBDOMAIN=""
ADMIN_EMAIL="${SHOGUN_ADMIN_EMAIL:-admin@localhost}"
DISPLAY_NAME="${SHOGUN_DISPLAY_NAME:-}"
WEB_PORT="${SHOGUN_WEB_PORT:-8787}"
WEB_HOST="${SHOGUN_WEB_HOST:-0.0.0.0}"
REGISTRY_URL="${SHOGUN_REGISTRY_URL:-https://registry.shogun-os.ai}"
REGISTRY_TOKEN="${SHOGUN_REGISTRY_TOKEN:-}"
DOMAIN_SUFFIX="${SHOGUN_DOMAIN_SUFFIX:-shogun-os.ai}"
GOOGLE_CLIENT_ID="${SHOGUN_GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${SHOGUN_GOOGLE_CLIENT_SECRET:-}"
MS_CLIENT_ID="${SHOGUN_MS_CLIENT_ID:-}"
MS_CLIENT_SECRET="${SHOGUN_MS_CLIENT_SECRET:-}"
MS_TENANT_ID="${SHOGUN_MS_TENANT_ID:-common}"

DRY_RUN=false
FORCE=false
SKIP_REGISTRY=false
SKIP_SYSTEMD=false
SKIP_UI_BUILD=false
SKIP_DEPT_SERVICES=false
START_SERVICES=true
CREATE_TUNNEL=true

# Python deps required by shogun-web
PYTHON_DEPS=(
  fastapi
  "uvicorn[standard]"
  sqlalchemy
  authlib
  httpx
  websockets
  "python-jose[cryptography]"
  "passlib[bcrypt]"
  pydantic
  python-multipart
  pyyaml
  aiosqlite
)

# Department catalogue: name|profile|port
DEFAULT_DEPARTMENTS=(
  "HR|hr-manager|9101"
  "Finance|finance-manager|9102"
  "Procurement|procurement-manager|9103"
  "CRM|crm-manager|9104"
  "Marketing|marketing-manager|9105"
  "Compliance|compliance-manager|9106"
  "Customer Support|customer-support|9107"
  "Project|project-manager|9108"
  "Product|product-manager|9109"
  "Coding|coding-agent|9110"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
info() { echo -e "  ${CYAN}💡${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠️${NC} $1"; }
err()  { echo -e "  ${RED}❌${NC} $1"; }
die()  { err "$1"; exit 1; }

usage() {
  cat <<EOF
Shogun OS Web Portal Installer v${VERSION}

Product:
  One company URL + one dashboard for all department agents.
  Subdomain is assigned randomly by our central registry/Cloudflare.
  Customers never need a Cloudflare account.

USAGE:
  ./scripts/install-web.sh [OPTIONS]

OPTIONS:
  --admin-email <email>    Admin login email (default: admin@localhost)
  --display-name <name>    Company display name
  --port <n>               shogun-web HTTP port (default: 8787)
  --host <addr>            Bind address (default: 0.0.0.0)
  --registry-url <url>     Central registry base URL
  --registry-token <tok>   Registration token (from us)
  --no-tunnel              Do not request per-tenant Cloudflare tunnel
  --vanity-subdomain <s>   Admin/escape-hatch only (ignored unless registry allows)
  --skip-registry          Do not POST /api/register
  --skip-systemd           Do not install systemd units
  --skip-ui-build          Skip npm install / build
  --skip-dept-services     Only create shogun-web unit (no hermes dept gateways)
  --no-start               Install units but do not enable/start them
  --force                  Overwrite existing web.json / credentials
  --dry-run                Preview actions only
  --help                   This message

DEPRECATED (still accepted, ignored for customer URL assignment):
  --subdomain <name>       Use --vanity-subdomain instead; random is default

ENVIRONMENT:
  SHOGUN_ADMIN_EMAIL, SHOGUN_DISPLAY_NAME
  SHOGUN_WEB_PORT, SHOGUN_WEB_HOST, SHOGUN_HOME, SHOGUN_WEB_DIR
  SHOGUN_REGISTRY_URL, SHOGUN_REGISTRY_TOKEN, SHOGUN_DOMAIN_SUFFIX
  SHOGUN_GOOGLE_CLIENT_ID, SHOGUN_GOOGLE_CLIENT_SECRET
  SHOGUN_MS_CLIENT_ID, SHOGUN_MS_CLIENT_SECRET, SHOGUN_MS_TENANT_ID

EXAMPLES:
  ./scripts/install-web.sh --admin-email admin@acme.com
  ./scripts/install-web.sh --dry-run
  ./scripts/install-web.sh --skip-registry --port 8080
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subdomain)
      # Back-compat: treat as vanity request (still ignored by default registry)
      VANITY_SUBDOMAIN="$2"
      warn "--subdomain is deprecated; URLs are assigned centrally. Treating as vanity request."
      shift 2
      ;;
    --vanity-subdomain)   VANITY_SUBDOMAIN="$2"; shift 2 ;;
    --admin-email)        ADMIN_EMAIL="$2"; shift 2 ;;
    --display-name)       DISPLAY_NAME="$2"; shift 2 ;;
    --port)               WEB_PORT="$2"; shift 2 ;;
    --host)               WEB_HOST="$2"; shift 2 ;;
    --registry-url)       REGISTRY_URL="$2"; shift 2 ;;
    --registry-token)     REGISTRY_TOKEN="$2"; shift 2 ;;
    --no-tunnel)          CREATE_TUNNEL=false; shift ;;
    --skip-registry)      SKIP_REGISTRY=true; shift ;;
    --skip-systemd)       SKIP_SYSTEMD=true; shift ;;
    --skip-ui-build)      SKIP_UI_BUILD=true; shift ;;
    --skip-dept-services) SKIP_DEPT_SERVICES=true; shift ;;
    --no-start)           START_SERVICES=false; shift ;;
    --force)              FORCE=true; shift ;;
    --dry-run)            DRY_RUN=true; shift ;;
    --help|-h)            usage ;;
    *) die "Unknown option: $1 (try --help)" ;;
  esac
done

# Resolve Python
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1 && python -c 'import sys' >/dev/null 2>&1; then
  PYTHON=python
else
  die "Python 3 is required"
fi

run() {
  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] $*"
    return 0
  fi
  "$@"
}

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g' | cut -c1-48
}

random_password() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 18 | tr -d '/+=' | cut -c1-20
  else
    "$PYTHON" -c 'import secrets,string; a=string.ascii_letters+string.digits; print("".join(secrets.choice(a) for _ in range(20)))'
  fi
}

random_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 16
  else
    "$PYTHON" -c 'import secrets; print(secrets.token_hex(16))'
  fi
}

hash_password() {
  local pw="$1"
  SHOGUN_HASH_PW="$pw" "$PYTHON" - <<'PY'
import os, hashlib, secrets
pw = os.environ.get("SHOGUN_HASH_PW", "")
try:
    from passlib.context import CryptContext
    print(CryptContext(schemes=["bcrypt"], deprecated="auto").hash(pw))
except Exception:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    print(f"pbkdf2_sha256$200000${salt}${h}")
PY
}

iso_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S"
}

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Shogun OS — Web Portal Installer v${VERSION}${NC}"
echo -e "${CYAN}  Repo:    ${REPO_ROOT}${NC}"
echo -e "${CYAN}  Home:    ${SHOGUN_HOME}${NC}"
[[ "$DRY_RUN" == true ]] && echo -e "${YELLOW}  Dry-run mode — no changes will be written${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

# ── 0. Preconditions ─────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Preconditions ━━━${NC}"

[[ -d "$SHOGUN_WEB_DIR" ]] || die "shogun-web not found at $SHOGUN_WEB_DIR"
ok "shogun-web directory: $SHOGUN_WEB_DIR"

[[ -d "$TEMPLATE_DIR" ]] || die "templates missing: $TEMPLATE_DIR"
ok "templates: $TEMPLATE_DIR"

# Resolve assigned subdomain: prefer existing install identity; never prompt.
# New installs use a local pending-* placeholder until the central registry
# assigns a random public slug (customers never pick URLs).
if [[ -z "$SUBDOMAIN" ]]; then
  if [[ -f "$SHOGUN_HOME/web.json" && "$FORCE" != true ]]; then
    SUBDOMAIN="$("$PYTHON" -c "import json; print(json.load(open('$SHOGUN_HOME/web.json')).get('subdomain',''))" 2>/dev/null || true)"
  fi
fi
if [[ -z "$SUBDOMAIN" ]]; then
  SUBDOMAIN="pending-$(random_hex | cut -c1-8)"
  info "Local placeholder until registry assigns URL: $SUBDOMAIN"
fi
SUBDOMAIN="$(slugify "$SUBDOMAIN")"
[[ -n "$SUBDOMAIN" ]] || die "subdomain is empty after sanitizing"
if [[ -z "$DISPLAY_NAME" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "  Company display name (optional): " DISPLAY_NAME || true
  fi
  DISPLAY_NAME="${DISPLAY_NAME:-My Company}"
fi
ok "Installer ready — public URL will be assigned by central registry (${DOMAIN_SUFFIX})"
info "One dashboard for all department agents (not separate portals per dept)"

# ── 1. Python dependencies ───────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ Python dependencies ━━━${NC}"

VENV_DIR="$SHOGUN_HOME/venv"
PIP_CMD=()

if [[ -d "$HERMES_HOME/hermes-agent/venv" ]]; then
  # Prefer Hermes venv so we share the environment
  # shellcheck disable=SC1091
  if [[ "$DRY_RUN" != true ]]; then
    # shellcheck source=/dev/null
    source "$HERMES_HOME/hermes-agent/venv/bin/activate" 2>/dev/null || true
  fi
  PIP_CMD=("$HERMES_HOME/hermes-agent/venv/bin/pip")
  ok "Using Hermes venv: $HERMES_HOME/hermes-agent/venv"
elif [[ -x "$VENV_DIR/bin/pip" ]]; then
  PIP_CMD=("$VENV_DIR/bin/pip")
  ok "Using existing Shogun venv: $VENV_DIR"
else
  info "Creating dedicated venv at $VENV_DIR"
  run mkdir -p "$SHOGUN_HOME"
  if [[ "$DRY_RUN" != true ]]; then
    "$PYTHON" -m venv "$VENV_DIR"
  fi
  PIP_CMD=("$VENV_DIR/bin/pip")
fi

if [[ "$DRY_RUN" == true ]]; then
  info "[DRY-RUN] Would pip install: ${PYTHON_DEPS[*]}"
else
  "${PIP_CMD[@]}" install --upgrade pip setuptools wheel >/dev/null
  if "${PIP_CMD[@]}" install "${PYTHON_DEPS[@]}"; then
    ok "Installed Python packages (${#PYTHON_DEPS[@]} specs)"
  else
    die "pip install failed"
  fi
fi

# Resolve python binary used at runtime
if [[ -x "${PIP_CMD[0]%/*}/python" ]]; then
  RUNTIME_PYTHON="${PIP_CMD[0]%/*}/python"
elif [[ -x "$HERMES_HOME/hermes-agent/venv/bin/python" ]]; then
  RUNTIME_PYTHON="$HERMES_HOME/hermes-agent/venv/bin/python"
elif [[ -x "$VENV_DIR/bin/python" ]]; then
  RUNTIME_PYTHON="$VENV_DIR/bin/python"
else
  RUNTIME_PYTHON="$PYTHON"
fi
info "Runtime Python: $RUNTIME_PYTHON"

# ── 2. Node / React frontend ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ Frontend (React) ━━━${NC}"

UI_DIR="$SHOGUN_WEB_DIR/ui"
STATIC_DIR="$UI_DIR/dist"

if [[ "$SKIP_UI_BUILD" == true ]]; then
  warn "Skipping UI build (--skip-ui-build)"
elif [[ ! -d "$UI_DIR" ]]; then
  warn "No ui/ directory at $UI_DIR — skip frontend build"
elif [[ ! -f "$UI_DIR/package.json" ]]; then
  warn "ui/package.json missing — skip frontend build"
else
  if ! command -v npm >/dev/null 2>&1; then
    warn "npm not found — skip frontend build (install Node.js 18+)"
  else
    ok "npm: $(npm --version 2>/dev/null || echo unknown)"
    if [[ "$DRY_RUN" == true ]]; then
      info "[DRY-RUN] Would npm ci/install + npm run build in $UI_DIR"
    else
      pushd "$UI_DIR" >/dev/null
      if [[ -f package-lock.json ]]; then
        npm ci --no-audit --no-fund || npm install --no-audit --no-fund
      else
        npm install --no-audit --no-fund
      fi
      npm run build
      popd >/dev/null
      if [[ -f "$STATIC_DIR/index.html" ]]; then
        ok "React build ready: $STATIC_DIR"
      else
        warn "Build finished but $STATIC_DIR/index.html not found"
      fi
    fi
  fi
fi

# ── 3. Data directories ───────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ Directories & secrets ━━━${NC}"

run mkdir -p "$SHOGUN_HOME"/{data,logs,secrets,static}
ok "Created $SHOGUN_HOME/{data,logs,secrets,static}"

DB_PATH="$SHOGUN_HOME/data/shogun-web.db"
LOG_PATH="$SHOGUN_HOME/logs/shogun-web.log"
CRED_FILE="$SHOGUN_HOME/secrets/admin-credentials.txt"
CONFIG_YAML="$SHOGUN_HOME/config.yaml"
WEB_JSON="$SHOGUN_HOME/web.json"

# Tenant id + password (idempotent: reuse unless --force)
TENANT_ID=""
ADMIN_PASSWORD=""
if [[ -f "$WEB_JSON" && "$FORCE" != true ]]; then
  TENANT_ID="$("$PYTHON" -c "import json; print(json.load(open('$WEB_JSON')).get('tenant_id',''))" 2>/dev/null || true)"
  info "Reusing existing web.json (use --force to regenerate)"
fi
if [[ -z "$TENANT_ID" ]]; then
  TENANT_ID="ten_$(random_hex)"
fi

if [[ -f "$CRED_FILE" && "$FORCE" != true ]]; then
  ADMIN_PASSWORD="$(grep -E '^password=' "$CRED_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true)"
fi
if [[ -z "$ADMIN_PASSWORD" ]]; then
  ADMIN_PASSWORD="$(random_password)"
fi
SECRET_KEY="$(random_hex)$(random_hex)"
if [[ -f "$CONFIG_YAML" && "$FORCE" != true ]]; then
  # keep previous secret if present
  EXISTING_SECRET="$("$PYTHON" - <<PY 2>/dev/null || true
import re
try:
    import yaml
    d=yaml.safe_load(open("$CONFIG_YAML"))
    print((d or {}).get("auth",{}).get("secret_key",""))
except Exception:
    t=open("$CONFIG_YAML").read()
    m=re.search(r'secret_key:\\s*[\"\\']?([^\"\\'\\n]+)', t)
    print(m.group(1) if m else "")
PY
)"
  if [[ -n "${EXISTING_SECRET:-}" ]]; then
    SECRET_KEY="$EXISTING_SECRET"
  fi
fi
ok "tenant_id=$TENANT_ID"

# ── 4. Generate web.json ─────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ Tenant config (web.json) ━━━${NC}"

CREATED_AT="$(iso_now)"
ADMIN_PASSWORD_HASH=""
if [[ "$DRY_RUN" != true ]]; then
  # Ensure passlib available for hash when possible
  ADMIN_PASSWORD_HASH="$(hash_password "$ADMIN_PASSWORD")"
else
  ADMIN_PASSWORD_HASH="DRY_RUN_HASH"
fi

if [[ -f "$WEB_JSON" && "$FORCE" != true ]]; then
  ok "Keeping existing $WEB_JSON"
else
  if [[ -f "$TEMPLATE_DIR/web.json" ]]; then
    TMP_JSON="$(mktemp)"
    sed \
      -e "s|{{TENANT_ID}}|${TENANT_ID}|g" \
      -e "s|{{SUBDOMAIN}}|${SUBDOMAIN}|g" \
      -e "s|{{DISPLAY_NAME}}|${DISPLAY_NAME}|g" \
      -e "s|{{ADMIN_EMAIL}}|${ADMIN_EMAIL}|g" \
      -e "s|{{ADMIN_PASSWORD_HASH}}|${ADMIN_PASSWORD_HASH}|g" \
      -e "s|{{CREATED_AT}}|${CREATED_AT}|g" \
      "$TEMPLATE_DIR/web.json" > "$TMP_JSON"
    # Patch server.port via Python for correctness
    if [[ "$DRY_RUN" == true ]]; then
      info "[DRY-RUN] Would write $WEB_JSON from template"
      rm -f "$TMP_JSON"
    else
      "$PYTHON" - "$TMP_JSON" "$WEB_JSON" "$WEB_PORT" "$WEB_HOST" "$DOMAIN_SUFFIX" <<'PY'
import json, sys
src, dest, port, host, suffix = sys.argv[1:6]
with open(src) as f:
    data = json.load(f)
data.setdefault("server", {})
data["server"]["host"] = host
data["server"]["port"] = int(port)
sub = data.get("subdomain", "tenant")
data["server"]["public_url"] = f"https://{sub}.{suffix}"
with open(dest, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
      rm -f "$TMP_JSON"
      ok "Wrote $WEB_JSON"
    fi
  else
    # Inline fallback
    if [[ "$DRY_RUN" == true ]]; then
      info "[DRY-RUN] Would write web.json (no template)"
    else
      "$PYTHON" - <<PY
import json
from pathlib import Path
depts = []
for row in """$(printf '%s\n' "${DEFAULT_DEPARTMENTS[@]}")""".strip().splitlines():
    name, profile, port = row.split("|")
    depts.append({"name": name, "profile": profile, "port": int(port), "status": "pending"})
data = {
  "tenant_id": "$TENANT_ID",
  "subdomain": "$SUBDOMAIN",
  "display_name": "$DISPLAY_NAME",
  "admin_user": {
    "email": "$ADMIN_EMAIL",
    "password_hash": "$ADMIN_PASSWORD_HASH",
    "display_name": "Admin",
  },
  "server": {
    "host": "$WEB_HOST",
    "port": int("$WEB_PORT"),
    "public_url": f"https://$SUBDOMAIN.$DOMAIN_SUFFIX",
  },
  "departments": depts,
  "onboarding": {"step": "welcome", "completed": False, "steps_done": []},
  "registry": {"registered": False, "registered_at": None, "last_heartbeat": None},
  "created_at": "$CREATED_AT",
  "updated_at": "$CREATED_AT",
}
Path("$WEB_JSON").write_text(json.dumps(data, indent=2) + "\n")
PY
      ok "Wrote $WEB_JSON (inline)"
    fi
  fi
fi

# Credentials file (plaintext password once — chmod 600)
if [[ "$DRY_RUN" == true ]]; then
  info "[DRY-RUN] Would write $CRED_FILE"
else
  umask 077
  cat > "$CRED_FILE" <<EOF
# Shogun OS web portal admin credentials
# Generated: $CREATED_AT
# KEEP SECRET — shown once at install time
email=$ADMIN_EMAIL
password=$ADMIN_PASSWORD
tenant_id=$TENANT_ID
subdomain=$SUBDOMAIN
public_url=https://${SUBDOMAIN}.${DOMAIN_SUFFIX}
local_url=http://127.0.0.1:${WEB_PORT}
EOF
  chmod 600 "$CRED_FILE" 2>/dev/null || true
  ok "Admin credentials saved: $CRED_FILE (mode 600)"
fi

# ── 5. config.yaml ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ Server config (config.yaml) ━━━${NC}"

STATIC_RESOLVED="$STATIC_DIR"
if [[ ! -d "$STATIC_RESOLVED" ]]; then
  STATIC_RESOLVED="$SHOGUN_HOME/static"
fi

if [[ -f "$CONFIG_YAML" && "$FORCE" != true ]]; then
  ok "Keeping existing $CONFIG_YAML"
else
  if [[ -f "$TEMPLATE_DIR/config.yaml" ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      info "[DRY-RUN] Would write $CONFIG_YAML"
    else
      sed \
        -e "s|{{HOST}}|${WEB_HOST}|g" \
        -e "s|{{PORT}}|${WEB_PORT}|g" \
        -e "s|{{DB_PATH}}|${DB_PATH}|g" \
        -e "s|{{STATIC_DIR}}|${STATIC_RESOLVED}|g" \
        -e "s|{{SECRET_KEY}}|${SECRET_KEY}|g" \
        -e "s|{{GOOGLE_CLIENT_ID}}|${GOOGLE_CLIENT_ID}|g" \
        -e "s|{{GOOGLE_CLIENT_SECRET}}|${GOOGLE_CLIENT_SECRET}|g" \
        -e "s|{{MS_CLIENT_ID}}|${MS_CLIENT_ID}|g" \
        -e "s|{{MS_CLIENT_SECRET}}|${MS_CLIENT_SECRET}|g" \
        -e "s|{{MS_TENANT_ID}}|${MS_TENANT_ID}|g" \
        -e "s|{{REGISTRY_URL}}|${REGISTRY_URL}|g" \
        -e "s|{{REGISTRY_TOKEN}}|${REGISTRY_TOKEN}|g" \
        -e "s|{{LOG_PATH}}|${LOG_PATH}|g" \
        "$TEMPLATE_DIR/config.yaml" > "$CONFIG_YAML"
      # Coerce port to integer if yaml parser wants int — leave quoted is fine for our server
      ok "Wrote $CONFIG_YAML"
    fi
  else
    die "Missing template: $TEMPLATE_DIR/config.yaml"
  fi
fi

# Soft-link repo static build into SHOGUN_HOME if useful
if [[ -d "$STATIC_DIR" && "$DRY_RUN" != true ]]; then
  ln -sfn "$STATIC_DIR" "$SHOGUN_HOME/static/ui-dist" 2>/dev/null || true
fi

# ── 6. Registry registration ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ Central registry (assigns your public URL) ━━━${NC}"

if [[ "$SKIP_REGISTRY" == true ]]; then
  warn "Skipping registry registration (--skip-registry)"
  info "Portal is local-only until you register: docs/architecture/WEB_PORTAL.md"
elif [[ "$DRY_RUN" == true ]]; then
  info "[DRY-RUN] Would bootstrap + POST ${REGISTRY_URL}/api/register"
else
  # Seamless path: if no operator token, mint a short-lived install ticket.
  # Customers never need REGISTRATION_TOKEN.
  if [[ -z "$REGISTRY_TOKEN" ]]; then
    info "Requesting install ticket from ${REGISTRY_URL}/api/install/bootstrap …"
    BOOT_BODY="$(mktemp)"
    set +e
    BOOT_CODE="$(curl -sS -o "$BOOT_BODY" -w '%{http_code}' -X POST \
      "${REGISTRY_URL%/}/api/install/bootstrap" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json" \
      -d "{\"email\":\"${ADMIN_EMAIL}\",\"display_name\":\"${DISPLAY_NAME}\",\"installer_version\":\"${VERSION}\"}" \
      --connect-timeout 8 --max-time 30 2>/dev/null || echo "000")"
    set -e
    if [[ "$BOOT_CODE" =~ ^2 ]]; then
      REGISTRY_TOKEN="$("$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1])).get('install_token',''))" "$BOOT_BODY" 2>/dev/null || true)"
      BOOT_DOMAIN="$("$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1])).get('domain',''))" "$BOOT_BODY" 2>/dev/null || true)"
      if [[ -n "$BOOT_DOMAIN" ]]; then
        DOMAIN_SUFFIX="$BOOT_DOMAIN"
      fi
      if [[ -n "$REGISTRY_TOKEN" ]]; then
        ok "Install ticket issued (single-use, short-lived)"
      else
        warn "Bootstrap OK but no install_token in response"
      fi
    else
      warn "Bootstrap failed (HTTP ${BOOT_CODE:-?}) — cannot register without ticket"
      info "Response: $(head -c 200 "$BOOT_BODY" 2>/dev/null || true)"
    fi
    rm -f "$BOOT_BODY"
  else
    info "Using provided registry token (operator / env override)"
  fi

  PAYLOAD="$(mktemp)"
  REG_BODY="$(mktemp)"
  # Payload matches registry RegisterRequest schema. Do NOT send customer-chosen
  # subdomain — central registry assigns adjective-noun-NN randomly.
  "$PYTHON" - <<PY > "$PAYLOAD"
import json
from pathlib import Path
web = {}
p = Path("$WEB_JSON")
if p.exists():
    web = json.loads(p.read_text())
tenant_id = web.get("tenant_id") or "$TENANT_ID"
payload = {
  "host": "127.0.0.1",
  "port": int("$WEB_PORT"),
  "create_tunnel": $( [[ "$CREATE_TUNNEL" == true ]] && echo true || echo false ),
  "tenant_id": tenant_id if tenant_id and not str(tenant_id).startswith("pending") else None,
  "metadata": {
    "display_name": "$DISPLAY_NAME",
    "admin_email": "$ADMIN_EMAIL",
    "local_url": f"http://127.0.0.1:$WEB_PORT",
    "version": "$VERSION",
    "departments": web.get("departments", []),
  },
}
tok = """$REGISTRY_TOKEN"""
if tok.strip():
    payload["registration_token"] = tok.strip()
vanity = """$(slugify "${VANITY_SUBDOMAIN}")""".strip()
if vanity:
    # Only honored when registry ALLOW_PREFERRED_SUBDOMAIN=true
    payload["preferred_subdomain"] = vanity
if payload.get("tenant_id") is None:
    payload.pop("tenant_id", None)
print(json.dumps(payload))
PY
  if ! command -v curl >/dev/null 2>&1; then
    warn "curl not found — cannot register with registry"
    rm -f "$PAYLOAD" "$REG_BODY"
  elif [[ -z "$REGISTRY_TOKEN" ]]; then
    warn "No install ticket or registry token — skipping register"
    rm -f "$PAYLOAD" "$REG_BODY"
  else
    set +e
    HTTP_CODE="$(curl -sS -o "$REG_BODY" -w '%{http_code}' -X POST "${REGISTRY_URL%/}/api/register" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json" \
      -d @"$PAYLOAD" --connect-timeout 8 --max-time 45 2>/dev/null || echo "000")"
    set -e
    BODY="$(cat "$REG_BODY" 2>/dev/null || true)"
    rm -f "$PAYLOAD" "$REG_BODY"
    if [[ "$HTTP_CODE" =~ ^2 ]]; then
      ok "Registered with central registry (HTTP $HTTP_CODE)"
      # Apply assigned subdomain + public_url + optional tunnel token
      REG_JSON_FILE="$(mktemp)"
      printf '%s' "$BODY" > "$REG_JSON_FILE"
      "$PYTHON" "$SCRIPT_DIR/apply-registry-response.py" \
        "$REG_JSON_FILE" "$WEB_JSON" "$CRED_FILE" "$SHOGUN_HOME" "$DOMAIN_SUFFIX" "$REGISTRY_URL" \
        >/dev/null || warn "Could not apply registry response to web.json"
      rm -f "$REG_JSON_FILE"
      ASSIGNED_SUB="$("$PYTHON" -c "import json;print(json.load(open('$WEB_JSON')).get('subdomain',''))" 2>/dev/null || true)"
      PUBLIC_URL="$("$PYTHON" -c "import json;print(json.load(open('$WEB_JSON')).get('server',{}).get('public_url',''))" 2>/dev/null || true)"
      if [[ -n "$ASSIGNED_SUB" ]]; then
        SUBDOMAIN="$ASSIGNED_SUB"
      fi
      if [[ -n "$PUBLIC_URL" ]]; then
        ok "Your portal URL: ${BOLD}${PUBLIC_URL}${NC}"
      else
        ok "Assigned subdomain: ${SUBDOMAIN}.${DOMAIN_SUFFIX}"
      fi
      if [[ -f "$SHOGUN_HOME/tunnel.token" ]]; then
        ok "Cloudflare tunnel token saved → $SHOGUN_HOME/tunnel.token"
        info "Run connector: cloudflared tunnel run --token \"\$(cat $SHOGUN_HOME/tunnel.token)\""
      fi
    else
      warn "Registry registration failed (HTTP ${HTTP_CODE:-?}) — portal still usable locally"
      info "Response: ${BODY:0:200}"
      info "Re-run later once registry is up, or use --skip-registry for local-only"
    fi
  fi
fi

# ── 7. Systemd units ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}━━━ systemd user services ━━━${NC}"

SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

# Discover entrypoint for shogun-web
SERVER_DIR="$SHOGUN_WEB_DIR/server"
ENTRY_MODULE="main"
if [[ -f "$SERVER_DIR/main.py" ]]; then
  ENTRY_MODULE="main"
elif [[ -f "$SERVER_DIR/app.py" ]]; then
  ENTRY_MODULE="app"
elif [[ -f "$SERVER_DIR/__main__.py" ]]; then
  ENTRY_MODULE="__main__"
fi

find_hermes_bin() {
  if command -v hermes >/dev/null 2>&1; then
    command -v hermes
  elif [[ -x "$HERMES_HOME/hermes-agent/venv/bin/hermes" ]]; then
    echo "$HERMES_HOME/hermes-agent/venv/bin/hermes"
  elif [[ -x "$HOME/.local/bin/hermes" ]]; then
    echo "$HOME/.local/bin/hermes"
  else
    echo "hermes"
  fi
}
HERMES_BIN="$(find_hermes_bin)"

if [[ "$SKIP_SYSTEMD" == true ]]; then
  warn "Skipping systemd (--skip-systemd)"
else
  run mkdir -p "$SYSTEMD_DIR"

  # shogun-web.service
  WEB_UNIT="$SYSTEMD_DIR/shogun-web.service"
  WEB_UNIT_CONTENT="[Unit]
Description=Shogun OS Web Portal
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
WorkingDirectory=${SERVER_DIR}
Environment=SHOGUN_HOME=${SHOGUN_HOME}
Environment=SHOGUN_CONFIG=${CONFIG_YAML}
Environment=SHOGUN_WEB_JSON=${WEB_JSON}
Environment=PYTHONPATH=${SERVER_DIR}:${SHOGUN_WEB_DIR}
Environment=PATH=$(dirname "$RUNTIME_PYTHON"):${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${RUNTIME_PYTHON} -m uvicorn ${ENTRY_MODULE}:app --host ${WEB_HOST} --port ${WEB_PORT} --app-dir ${SERVER_DIR}
Restart=always
RestartSec=5
TimeoutStopSec=30
StandardOutput=append:${LOG_PATH}
StandardError=append:${LOG_PATH}

[Install]
WantedBy=default.target
"

  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would write $WEB_UNIT"
  else
    printf '%s\n' "$WEB_UNIT_CONTENT" > "$WEB_UNIT"
    ok "Installed shogun-web.service"
  fi

  # Per-department hermes serve units
  if [[ "$SKIP_DEPT_SERVICES" == true ]]; then
    warn "Skipping department gateway services"
  else
    # Prefer departments from web.json when present
    DEPT_LINES=()
    if [[ -f "$WEB_JSON" ]]; then
      mapfile -t DEPT_LINES < <("$PYTHON" - <<'PY' "$WEB_JSON"
import json, sys
data = json.load(open(sys.argv[1]))
for d in data.get("departments", []):
    print(f"{d.get('name','')}|{d.get('profile','')}|{d.get('port',0)}")
PY
)
    fi
    if [[ ${#DEPT_LINES[@]} -eq 0 ]]; then
      DEPT_LINES=("${DEFAULT_DEPARTMENTS[@]}")
    fi

    for row in "${DEPT_LINES[@]}"; do
      IFS='|' read -r dname dprofile dport <<<"$row"
      [[ -n "$dprofile" && -n "$dport" && "$dport" != "0" ]] || continue
      unit_name="shogun-hermes@${dprofile}.service"
      # Prefer template unit if we can write one, plus a concrete unit for hermes serve port
      unit_path="$SYSTEMD_DIR/shogun-dept-${dprofile}.service"
      unit_body="[Unit]
Description=Shogun OS Hermes Gateway — ${dname} (${dprofile})
After=network-online.target shogun-web.service
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
Environment=HERMES_HOME=${HERMES_HOME}
Environment=PATH=$(dirname "$HERMES_BIN"):${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=${HERMES_HOME}
ExecStart=${HERMES_BIN} -p ${dprofile} serve --port ${dport}
Restart=always
RestartSec=5
TimeoutStopSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"
      if [[ "$DRY_RUN" == true ]]; then
        info "[DRY-RUN] Would write $unit_path (port $dport)"
      else
        printf '%s\n' "$unit_body" > "$unit_path"
        ok "Unit: shogun-dept-${dprofile}.service → :${dport}"
      fi
    done

    # Also install a template unit for convenience
    TPL="$SYSTEMD_DIR/shogun-dept@.service"
    TPL_BODY="[Unit]
Description=Shogun OS Hermes Dept Gateway — %i
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
Environment=HERMES_HOME=${HERMES_HOME}
Environment=PATH=$(dirname "$HERMES_BIN"):${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=${HERMES_HOME}
# Port must be provided via drop-in or environment file:
#   ~/.config/systemd/user/shogun-dept@%i.service.d/port.conf
#   [Service]
#   Environment=SHOGUN_DEPT_PORT=91xx
#   ExecStart=
#   ExecStart=${HERMES_BIN} -p %i serve --port \${SHOGUN_DEPT_PORT}
ExecStart=${HERMES_BIN} -p %i serve
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"
    if [[ "$DRY_RUN" == true ]]; then
      info "[DRY-RUN] Would write $TPL"
    else
      printf '%s\n' "$TPL_BODY" > "$TPL"
      ok "Template unit: shogun-dept@.service"
    fi
  fi

  if [[ "$DRY_RUN" != true ]]; then
    systemctl --user daemon-reload 2>/dev/null || warn "systemctl --user daemon-reload failed (no user session?)"
    ok "systemd daemon-reload"

    if command -v loginctl >/dev/null 2>&1; then
      linger="$(loginctl show-user "$USER" 2>/dev/null | grep '^Linger=' | cut -d= -f2 || echo no)"
      if [[ "$linger" != "yes" ]]; then
        warn "User lingering disabled — services stop on logout"
        info "Enable: sudo loginctl enable-linger $USER"
      else
        ok "Lingering enabled"
      fi
    fi

    if [[ "$START_SERVICES" == true ]]; then
      systemctl --user enable --now shogun-web.service 2>/dev/null && ok "Enabled+started shogun-web.service" \
        || warn "Could not start shogun-web (server app may not exist yet — unit is installed)"

      if [[ "$SKIP_DEPT_SERVICES" != true ]]; then
        for row in "${DEPT_LINES[@]:-}"; do
          IFS='|' read -r _dname dprofile _dport <<<"$row"
          [[ -n "${dprofile:-}" ]] || continue
          # Only start if profile directory exists
          if [[ -d "$HERMES_HOME/profiles/$dprofile" ]] || hermes profile list 2>/dev/null | grep -q "$dprofile"; then
            systemctl --user enable --now "shogun-dept-${dprofile}.service" 2>/dev/null \
              && ok "Started shogun-dept-${dprofile}.service" \
              || warn "Could not start shogun-dept-${dprofile}.service"
          else
            info "Profile not installed yet: $dprofile — unit written, not started"
          fi
        done
      fi
    else
      info "Units installed but not started (--no-start)"
    fi
  fi
fi

# ── 8. Summary ───────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Install complete${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BOLD}Access${NC}"
echo -e "  Public URL : ${GREEN}https://${SUBDOMAIN}.${DOMAIN_SUFFIX}${NC}"
echo -e "  Local URL  : ${GREEN}http://127.0.0.1:${WEB_PORT}${NC}"
echo -e "  Admin email: ${GREEN}${ADMIN_EMAIL}${NC}"
echo -e "  Password   : ${GREEN}${ADMIN_PASSWORD}${NC}"
echo -e "  Credentials: ${CYAN}${CRED_FILE}${NC}"
echo ""
echo -e "${BOLD}Config${NC}"
echo -e "  SHOGUN_HOME : $SHOGUN_HOME"
echo -e "  web.json    : $WEB_JSON"
echo -e "  config.yaml : $CONFIG_YAML"
echo -e "  database    : $DB_PATH"
echo -e "  tenant_id   : $TENANT_ID"
echo ""
echo -e "${BOLD}Next steps${NC}"
echo -e "  1. Visit ${GREEN}http://127.0.0.1:${WEB_PORT}${NC} (or your public URL)"
echo -e "  2. Log in with the admin email/password above"
echo -e "  3. Complete onboarding (company details, departments, integrations)"
echo -e "  4. Deploy department profiles if needed:  ${CYAN}./scripts/install.sh --deploy${NC}"
echo -e "  5. Verify portal health:                  ${CYAN}./scripts/verify-web.sh${NC}"
echo -e "  6. Change the admin password after first login"
echo ""
if [[ "$DRY_RUN" == true ]]; then
  warn "Dry-run only — re-run without --dry-run to apply"
fi

exit 0

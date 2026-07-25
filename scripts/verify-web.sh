#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Shogun OS — Web Portal Verification
# ──────────────────────────────────────────────────────────────────────────
# Checks shogun-web service, database, registry, department gateways,
# React build, and config files. Idempotent / read-only (except --fix).
#
# Usage:
#   ./scripts/verify-web.sh
#   ./scripts/verify-web.sh --quick
#   ./scripts/verify-web.sh --fix
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$SCRIPT_DIR/.." && pwd)")"
SHOGUN_WEB_DIR="${SHOGUN_WEB_DIR:-$REPO_ROOT/shogun-web}"
SHOGUN_HOME="${SHOGUN_HOME:-$HOME/.shogun-os}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DOMAIN_SUFFIX="${SHOGUN_DOMAIN_SUFFIX:-shogun.os}"

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

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  PYTHON=python3
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick) QUICK=true; shift ;;
    --fix)   FIX=true; shift ;;
    --help|-h)
      echo "Usage: $0 [--quick] [--fix]"
      echo "  --quick  Skip slow network / deep DB checks"
      echo "  --fix    Attempt limited repairs (daemon-reload, restart web)"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Shogun OS — Web Portal Verification${NC}"
echo -e "${CYAN}  SHOGUN_HOME: ${SHOGUN_HOME}${NC}"
[[ "$QUICK" == true ]] && echo -e "${YELLOW}  Quick mode${NC}"
[[ "$FIX" == true ]] && echo -e "${YELLOW}  Fix mode enabled${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

WEB_JSON="$SHOGUN_HOME/web.json"
CONFIG_YAML="$SHOGUN_HOME/config.yaml"
DB_PATH="$SHOGUN_HOME/data/shogun-web.db"
UI_DIST="$SHOGUN_WEB_DIR/ui/dist"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

# Load tenant fields if present
TENANT_ID=""
SUBDOMAIN=""
WEB_PORT="8787"
if [[ -f "$WEB_JSON" ]]; then
  TENANT_ID="$("$PYTHON" -c "import json; print(json.load(open('$WEB_JSON')).get('tenant_id',''))" 2>/dev/null || true)"
  SUBDOMAIN="$("$PYTHON" -c "import json; print(json.load(open('$WEB_JSON')).get('subdomain',''))" 2>/dev/null || true)"
  WEB_PORT="$("$PYTHON" -c "import json; print(json.load(open('$WEB_JSON')).get('server',{}).get('port',8787))" 2>/dev/null || echo 8787)"
fi
if [[ -f "$CONFIG_YAML" ]]; then
  CFG_PORT="$("$PYTHON" - <<PY 2>/dev/null || true
import re
try:
    import yaml
    d=yaml.safe_load(open("$CONFIG_YAML")) or {}
    print(d.get("server",{}).get("port",""))
except Exception:
    t=open("$CONFIG_YAML").read()
    m=re.search(r'^\s*port:\s*[\"\\']?(\d+)', t, re.M)
    print(m.group(1) if m else "")
PY
)"
  if [[ -n "${CFG_PORT:-}" ]]; then
    WEB_PORT="$CFG_PORT"
  fi
  CFG_DB="$("$PYTHON" - <<PY 2>/dev/null || true
import re
try:
    import yaml
    d=yaml.safe_load(open("$CONFIG_YAML")) or {}
    print(d.get("database",{}).get("path",""))
except Exception:
    t=open("$CONFIG_YAML").read()
    m=re.search(r'path:\s*[\"\\']?([^\"\\'\\n]+)', t)
    print(m.group(1).strip() if m else "")
PY
)"
  if [[ -n "${CFG_DB:-}" ]]; then
    DB_PATH="$CFG_DB"
  fi
fi

# ── 1. Config files ──────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Config files ━━━${NC}"

if [[ -d "$SHOGUN_HOME" ]]; then
  ok "SHOGUN_HOME exists: $SHOGUN_HOME"
else
  fail "SHOGUN_HOME missing: $SHOGUN_HOME"
  if [[ "$FIX" == true ]]; then
    mkdir -p "$SHOGUN_HOME"/{data,logs,secrets,static}
    warn "[FIX] Created $SHOGUN_HOME skeleton — re-run install-web.sh"
  fi
fi

if [[ -f "$WEB_JSON" ]]; then
  if "$PYTHON" -c "import json; json.load(open('$WEB_JSON'))" 2>/dev/null; then
    ok "web.json present and valid JSON"
    info "tenant_id=${TENANT_ID:-?} subdomain=${SUBDOMAIN:-?}"
  else
    fail "web.json is not valid JSON: $WEB_JSON"
  fi
else
  fail "web.json missing: $WEB_JSON"
fi

if [[ -f "$CONFIG_YAML" ]]; then
  ok "config.yaml present: $CONFIG_YAML"
else
  fail "config.yaml missing: $CONFIG_YAML"
fi

if [[ -f "$SHOGUN_HOME/secrets/admin-credentials.txt" ]]; then
  ok "admin-credentials.txt present"
else
  warn "admin-credentials.txt missing (password only shown at install)"
fi

if [[ -f "$REPO_ROOT/templates/web-portal/config.yaml" ]]; then
  ok "Repo template config.yaml available"
else
  warn "Repo template missing: templates/web-portal/config.yaml"
fi

if [[ -f "$REPO_ROOT/templates/web-portal/web.json" ]]; then
  ok "Repo template web.json available"
else
  warn "Repo template missing: templates/web-portal/web.json"
fi

echo ""

# ── 2. React build ───────────────────────────────────────────────────────
echo -e "${CYAN}━━━ React frontend build ━━━${NC}"

if [[ -d "$SHOGUN_WEB_DIR/ui" ]]; then
  ok "ui/ directory exists"
  if [[ -f "$UI_DIST/index.html" ]]; then
    ok "Production build present: $UI_DIST/index.html"
  else
    fail "React build missing ($UI_DIST/index.html)"
    if [[ "$FIX" == true ]] && command -v npm >/dev/null 2>&1; then
      info "[FIX] Running npm run build…"
      (cd "$SHOGUN_WEB_DIR/ui" && npm install --no-audit --no-fund && npm run build) \
        && ok "[FIX] Build completed" || fail "[FIX] Build failed"
    else
      info "Run: cd $SHOGUN_WEB_DIR/ui && npm install && npm run build"
    fi
  fi
  if [[ -L "$SHOGUN_HOME/static/ui-dist" || -d "$SHOGUN_HOME/static/ui-dist" ]]; then
    ok "static/ui-dist link or dir present under SHOGUN_HOME"
  else
    warn "No $SHOGUN_HOME/static/ui-dist (optional)"
  fi
else
  warn "No ui/ under shogun-web — frontend not packaged yet"
fi

echo ""

# ── 3. Database ──────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Database ━━━${NC}"

if [[ -f "$DB_PATH" ]]; then
  ok "Database file exists: $DB_PATH"
  if [[ "$QUICK" != true ]]; then
    if command -v sqlite3 >/dev/null 2>&1; then
      TABLES="$(sqlite3 "$DB_PATH" ".tables" 2>/dev/null || true)"
      if [[ -n "$(echo "$TABLES" | tr -d '[:space:]')" ]]; then
        ok "Database has tables: $(echo "$TABLES" | tr '\n' ' ' | xargs)"
      else
        warn "Database file exists but has no tables (app may create on first boot)"
      fi
    else
      # Fallback via Python
      TCOUNT="$("$PYTHON" - <<PY 2>/dev/null || echo 0
import sqlite3
c=sqlite3.connect("$DB_PATH")
n=c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
print(n)
names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
print(" ".join(names), file=__import__('sys').stderr)
PY
)"
      if [[ "${TCOUNT:-0}" -gt 0 ]]; then
        ok "Database has $TCOUNT user table(s)"
      else
        warn "Database has no user tables yet (first-run migrate)"
      fi
    fi
  fi
else
  warn "Database not created yet: $DB_PATH"
  info "Usually created on first shogun-web start"
fi

echo ""

# ── 4. shogun-web service ────────────────────────────────────────────────
echo -e "${CYAN}━━━ shogun-web service ━━━${NC}"

UNIT_WEB="$SYSTEMD_DIR/shogun-web.service"
if [[ -f "$UNIT_WEB" ]]; then
  ok "Unit file installed: $UNIT_WEB"
else
  fail "Unit file missing: $UNIT_WEB"
  info "Run: ./scripts/install-web.sh"
fi

if systemctl --user status shogun-web.service >/dev/null 2>&1; then
  # active?
  STATE="$(systemctl --user is-active shogun-web.service 2>/dev/null || echo unknown)"
  if [[ "$STATE" == "active" ]]; then
    ok "shogun-web.service is active"
  else
    fail "shogun-web.service state: $STATE"
    if [[ "$FIX" == true ]]; then
      systemctl --user daemon-reload 2>/dev/null || true
      systemctl --user restart shogun-web.service 2>/dev/null \
        && ok "[FIX] restarted shogun-web.service" \
        || warn "[FIX] restart failed (server code may be incomplete)"
    fi
  fi
else
  # systemctl unavailable or unit never loaded
  if ! command -v systemctl >/dev/null 2>&1; then
    warn "systemctl not available — skip service state check"
  else
    STATE="$(systemctl --user is-active shogun-web.service 2>/dev/null || echo inactive)"
    if [[ "$STATE" == "active" ]]; then
      ok "shogun-web.service is active"
    else
      fail "shogun-web.service not running (state=$STATE)"
      if [[ "$FIX" == true && -f "$UNIT_WEB" ]]; then
        systemctl --user daemon-reload 2>/dev/null || true
        systemctl --user enable --now shogun-web.service 2>/dev/null \
          && ok "[FIX] enabled shogun-web.service" \
          || warn "[FIX] could not start shogun-web.service"
      fi
    fi
  fi
fi

# HTTP health (local)
if command -v curl >/dev/null 2>&1 && [[ "$QUICK" != true ]]; then
  CODE="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 \
    "http://127.0.0.1:${WEB_PORT}/" 2>/dev/null || echo "000")"
  if [[ "$CODE" =~ ^(200|301|302|304|401|403)$ ]]; then
    ok "Local HTTP responds on :${WEB_PORT} (HTTP $CODE)"
  else
    # try /health
    CODE2="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 \
      "http://127.0.0.1:${WEB_PORT}/health" 2>/dev/null || echo "000")"
    if [[ "$CODE2" =~ ^(200|204)$ ]]; then
      ok "Local /health OK on :${WEB_PORT}"
    else
      warn "No HTTP response on 127.0.0.1:${WEB_PORT} (/$CODE /health=$CODE2)"
    fi
  fi
fi

echo ""

# ── 5. Department gateways ───────────────────────────────────────────────
echo -e "${CYAN}━━━ Department Hermes gateways ━━━${NC}"

DEPT_ROWS=()
if [[ -f "$WEB_JSON" ]]; then
  mapfile -t DEPT_ROWS < <("$PYTHON" - <<'PY' "$WEB_JSON" 2>/dev/null || true
import json, sys
for d in json.load(open(sys.argv[1])).get("departments", []):
    print(f"{d.get('name','')}|{d.get('profile','')}|{d.get('port',0)}|{d.get('status','')}")
PY
)
fi

if [[ ${#DEPT_ROWS[@]} -eq 0 ]]; then
  warn "No departments listed in web.json"
else
  for row in "${DEPT_ROWS[@]}"; do
    IFS='|' read -r dname dprofile dport dstatus <<<"$row"
    [[ -n "$dprofile" ]] || continue
    unit="shogun-dept-${dprofile}.service"
    unit_path="$SYSTEMD_DIR/$unit"
    label="${dname:-$dprofile} (:${dport})"

    if [[ -f "$unit_path" ]]; then
      ok "Unit installed: $unit"
    else
      fail "Unit missing: $unit_path"
      continue
    fi

    if command -v systemctl >/dev/null 2>&1; then
      st="$(systemctl --user is-active "$unit" 2>/dev/null || echo inactive)"
      if [[ "$st" == "active" ]]; then
        ok "Gateway running: $label"
      else
        # Profile may not be installed — softer failure
        if [[ -d "$HERMES_HOME/profiles/$dprofile" ]]; then
          fail "Gateway not running: $label (state=$st)"
          if [[ "$FIX" == true ]]; then
            systemctl --user enable --now "$unit" 2>/dev/null \
              && ok "[FIX] started $unit" || warn "[FIX] failed to start $unit"
          fi
        else
          warn "Gateway not running: $label — profile not installed"
        fi
      fi
    fi

    if [[ "$QUICK" != true ]] && command -v curl >/dev/null 2>&1 && [[ -n "$dport" && "$dport" != "0" ]]; then
      pc="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 1 --max-time 2 \
        "http://127.0.0.1:${dport}/" 2>/dev/null || echo "000")"
      if [[ "$pc" != "000" ]]; then
        ok "  └─ port ${dport} accepts TCP/HTTP ($pc)"
      fi
    fi
  done
fi

echo ""

# ── 6. Registry / DNS ────────────────────────────────────────────────────
echo -e "${CYAN}━━━ Registry / subdomain ━━━${NC}"

if [[ -z "$SUBDOMAIN" ]]; then
  warn "No subdomain in web.json — skip registry/DNS checks"
else
  HOST_FQDN="${SUBDOMAIN}.${DOMAIN_SUFFIX}"
  info "Expected host: $HOST_FQDN"

  REG_FLAG="$("$PYTHON" -c "import json; print(json.load(open('$WEB_JSON')).get('registry',{}).get('registered', False))" 2>/dev/null || echo False)"
  if [[ "$REG_FLAG" == "True" || "$REG_FLAG" == "true" ]]; then
    ok "web.json marks registry.registered=true"
  else
    warn "web.json registry.registered is not true"
  fi

  if [[ "$QUICK" != true ]]; then
    RESOLVED=false
    if command -v getent >/dev/null 2>&1; then
      if getent hosts "$HOST_FQDN" >/dev/null 2>&1; then
        ok "DNS resolves: $HOST_FQDN"
        RESOLVED=true
      fi
    fi
    if [[ "$RESOLVED" != true ]] && command -v dig >/dev/null 2>&1; then
      if dig +short "$HOST_FQDN" 2>/dev/null | grep -q .; then
        ok "DNS resolves (dig): $HOST_FQDN"
        RESOLVED=true
      fi
    fi
    if [[ "$RESOLVED" != true ]] && command -v nslookup >/dev/null 2>&1; then
      if nslookup "$HOST_FQDN" >/dev/null 2>&1; then
        ok "DNS resolves (nslookup): $HOST_FQDN"
        RESOLVED=true
      fi
    fi
    if [[ "$RESOLVED" != true ]] && command -v host >/dev/null 2>&1; then
      if host "$HOST_FQDN" >/dev/null 2>&1; then
        ok "DNS resolves (host): $HOST_FQDN"
        RESOLVED=true
      fi
    fi
    if [[ "$RESOLVED" != true ]]; then
      warn "Subdomain does not resolve yet: $HOST_FQDN"
      info "Local access still works via http://127.0.0.1:${WEB_PORT}"
    fi

    if command -v curl >/dev/null 2>&1 && [[ "$RESOLVED" == true ]]; then
      RCODE="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 8 \
        "https://${HOST_FQDN}/" 2>/dev/null || echo "000")"
      if [[ "$RCODE" =~ ^(200|301|302|401|403)$ ]]; then
        ok "HTTPS reachable: https://${HOST_FQDN}/ ($RCODE)"
      else
        warn "HTTPS not ready for ${HOST_FQDN} (HTTP $RCODE)"
      fi
    fi
  fi
fi

echo ""

# ── 7. Python deps smoke ─────────────────────────────────────────────────
echo -e "${CYAN}━━━ Python packages ━━━${NC}"

check_pkg() {
  local pkg="$1"
  if "$PYTHON" -c "import $pkg" 2>/dev/null; then
    ok "import $pkg"
  else
    # try venv pythons
    local py
    for py in "$SHOGUN_HOME/venv/bin/python" "$HERMES_HOME/hermes-agent/venv/bin/python"; do
      if [[ -x "$py" ]] && "$py" -c "import $pkg" 2>/dev/null; then
        ok "import $pkg (via $py)"
        return
      fi
    done
    fail "missing Python package: $pkg"
  fi
}

if [[ "$QUICK" != true ]]; then
  check_pkg fastapi
  check_pkg uvicorn
  check_pkg sqlalchemy
  check_pkg httpx
  check_pkg yaml
else
  info "Skipped package imports (--quick)"
fi

echo ""

# ── Summary ──────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL + WARN))
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Summary${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}PASS${NC}: $PASS"
echo -e "  ${YELLOW}WARN${NC}: $WARN"
echo -e "  ${RED}FAIL${NC}: $FAIL"
echo -e "  Total checks counted: $TOTAL"
echo ""

if [[ -n "$SUBDOMAIN" ]]; then
  echo -e "  Public : https://${SUBDOMAIN}.${DOMAIN_SUFFIX}"
fi
echo -e "  Local  : http://127.0.0.1:${WEB_PORT}"
echo -e "  Config : $WEB_JSON"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  echo -e "  ${RED}Verification finished with failures.${NC}"
  echo -e "  Re-run installer: ${CYAN}./scripts/install-web.sh${NC}"
  echo -e "  Or attempt fixes:  ${CYAN}./scripts/verify-web.sh --fix${NC}"
  exit 1
fi

if [[ "$WARN" -gt 0 ]]; then
  echo -e "  ${YELLOW}Verification OK with warnings.${NC}"
  exit 0
fi

echo -e "  ${GREEN}All checks passed.${NC}"
exit 0

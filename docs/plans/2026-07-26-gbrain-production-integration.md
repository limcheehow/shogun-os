# GBrain Integration for Shogun OS — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Upgrade Shogun OS's GBrain integration from ad-hoc per-profile stdio to a production-grade, zero-cost, multi-transport knowledge layer with local embeddings, local Postgres, department schema pack, and automated maintenance.

**Architecture:** Single local Postgres 16 instance as the brain database. Ollama local embeddings (zero API cost). 11 department sources with federated `shared/`. Dual MCP transport — stdio for Hermes profiles, HTTP for the web portal. Nightly dream cycle at 2am. pg_dump backups (git push deferred).

**Tech Stack:** GBrain v0.42.53, PostgreSQL 16, Ollama (nomic-embed-text), pgvector, Bash + Python provisioning scripts, YAML schema pack.

---

## Current State (as of 2026-07-26)

| Component | Current | Target |
|-----------|---------|--------|
| Engine | Postgres @ `127.0.0.1:5432/gbrain` (local PG16) | ✅ Already correct — keep |
| Embedding | `openai:text-embedding-3-small` (1536d, $$) | `ollama:nomic-embed-text` (768d, $0) |
| Sources | 11 sources exist (shared + 10 depts) | ✅ Already correct — keep |
| Schema pack | `gbrain-base` (generic) | `shogun-enterprise` (department types) |
| MCP transport | stdio only (per-profile) | stdio (profiles) + HTTP (web portal) |
| Dream cycle | Not scheduled | Nightly 2am via cron |
| Backup | None automated | pg_dump nightly (git push deferred) |
| Federated read | `shared/` federated | ✅ Already correct — keep |
| Ollama | Not installed/running | Install + pull nomic-embed-text |

---

## Task 1: Install Ollama + Pull Embedding Model

**Objective:** Set up local embedding inference with zero API cost.

**Files:**
- Modify: `scripts/init-gbrain.sh` (add Ollama check step)

**Step 1: Install Ollama**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Step 2: Start Ollama service**

```bash
systemctl enable ollama
systemctl start ollama
```

**Step 3: Pull the embedding model**

```bash
ollama pull nomic-embed-text
```

**Step 4: Verify Ollama is serving**

```bash
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['name']) for m in d.get('models',[])]"
```

Expected: `nomic-embed-text:latest`

**Step 5: Smoke-test embedding via gbrain**

```bash
gbrain providers test --model ollama:nomic-embed-text
```

**Step 6: Commit**

```bash
git add scripts/init-gbrain.sh
git commit -m "feat: add Ollama local embedding setup to gbrain init"
```

---

## Task 2: Migrate Embeddings from OpenAI to Ollama

**Objective:** Switch the brain's embedding provider from OpenAI (paid) to Ollama (free). This requires re-embedding all existing chunks.

**Context:** Current brain has ~33.9K pages embedded at 1536d via OpenAI. Ollama nomic-embed-text is 768d. This is a `retrieval-upgrade` operation — gbrain handles the schema column resize + re-embed.

**Step 1: Verify current embedding config**

```bash
gbrain config get embedding_model
gbrain config get embedding_dimensions
```

Expected: `openai:text-embedding-3-small` / `1536`

**Step 2: Run retrieval-upgrade with reindex**

```bash
gbrain retrieval-upgrade --to ollama:nomic-embed-text --reindex
```

This will:
- ALTER the embedding column from 1536d to 768d
- Clear stale embeddings
- Re-embed all chunks via Ollama
- Update config to `embedding_model: ollama:nomic-embed-text`, `embedding_dimensions: 768`

**⚠️ Warning:** This will take significant time for 33.9K pages. Run with `--dry-run` first to estimate.

**Step 3: Verify new config**

```bash
gbrain config get embedding_model
gbrain config get embedding_dimensions
```

Expected: `ollama:nomic-embed-text` / `768`

**Step 4: Test search quality**

```bash
gbrain query "test query" --limit 3
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: migrate embeddings from OpenAI to Ollama local (768d, $0 cost)"
```

---

## Task 3: Create shogun-enterprise Schema Pack

**Objective:** Author a schema pack with department-specific page types, link types, and routing rules.

**Files:**
- Create: `~/.gbrain/schema-packs/shogun-enterprise/pack.yaml`

**Step 1: Scaffold the pack**

```bash
gbrain schema init shogun-enterprise
```

**Step 2: Write the pack manifest**

Create `~/.gbrain/schema-packs/shogun-enterprise/pack.yaml`:

```yaml
api_version: gbrain-schema-pack-v1
name: shogun-enterprise
version: 1.0.0
description: |
  Shogun OS enterprise schema pack — department-specific page types,
  link verbs, and expert routing for 10 department profiles + shared.
gbrain_min_version: 0.39.0
extends: gbrain-base
borrow_from: []

takes_kinds:
  - fact
  - take
  - bet
  - hunch

page_types:
  # ── Shared / Cross-department ──
  - name: staff
    primitive: entity
    path_prefixes:
      - shared/staff/
    aliases: [employee, team-member]
    extractable: true
    expert_routing: true

  - name: policy
    primitive: concept
    path_prefixes:
      - shared/policies/
    aliases: [sop, procedure]
    extractable: true
    expert_routing: false

  # ── HR ──
  - name: leave-request
    primitive: temporal
    path_prefixes:
      - hr/leave/
    aliases: [leave, time-off]
    extractable: true
    expert_routing: false

  - name: candidate
    primitive: entity
    path_prefixes:
      - hr/candidates/
    aliases: [applicant, interviewee]
    extractable: true
    expert_routing: true

  - name: review
    primitive: temporal
    path_prefixes:
      - hr/reviews/
    aliases: [performance-review, appraisal]
    extractable: true
    expert_routing: false

  # ── Finance ──
  - name: budget
    primitive: entity
    path_prefixes:
      - finance/budgets/
    aliases: [budget-line]
    extractable: true
    expert_routing: true

  - name: expense
    primitive: temporal
    path_prefixes:
      - finance/expenses/
    aliases: [receipt, reimbursement]
    extractable: true
    expert_routing: false

  - name: invoice
    primitive: temporal
    path_prefixes:
      - finance/invoices/
    aliases: [bill]
    extractable: true
    expert_routing: false

  # ── Projects ──
  - name: milestone
    primitive: temporal
    path_prefixes:
      - projects/milestones/
    aliases: [deliverable]
    extractable: true
    expert_routing: false

  - name: ticket
    primitive: temporal
    path_prefixes:
      - projects/tickets/
      - support/tickets/
    aliases: [issue, bug, support-request]
    extractable: true
    expert_routing: false

  # ── Procurement ──
  - name: vendor
    primitive: entity
    path_prefixes:
      - procurement/vendors/
    aliases: [supplier]
    extractable: true
    expert_routing: true

  - name: purchase-order
    primitive: temporal
    path_prefixes:
      - procurement/pos/
    aliases: [po]
    extractable: true
    expert_routing: false

  - name: contract
    primitive: temporal
    path_prefixes:
      - procurement/contracts/
    aliases: [agreement]
    extractable: true
    expert_routing: false

  # ── Products ──
  - name: prd
    primitive: media
    path_prefixes:
      - products/prds/
    aliases: [product-requirement]
    extractable: true
    expert_routing: false

  - name: roadmap
    primitive: temporal
    path_prefixes:
      - products/roadmaps/
    aliases: [product-roadmap]
    extractable: true
    expert_routing: false

  - name: release
    primitive: temporal
    path_prefixes:
      - products/releases/
    aliases: [version, changelog]
    extractable: true
    expert_routing: false

  # ── CRM ──
  - name: deal
    primitive: entity
    path_prefixes:
      - crm/deals/
    aliases: [opportunity]
    extractable: true
    expert_routing: true

  - name: contact
    primitive: entity
    path_prefixes:
      - crm/contacts/
    aliases: [lead, prospect]
    extractable: true
    expert_routing: true

  - name: company
    primitive: entity
    path_prefixes:
      - crm/companies/
    aliases: [account, organization]
    extractable: true
    expert_routing: true

  # ── Marketing ──
  - name: campaign
    primitive: temporal
    path_prefixes:
      - marketing/campaigns/
    aliases: [marketing-campaign]
    extractable: true
    expert_routing: false

  - name: content
    primitive: media
    path_prefixes:
      - marketing/content/
    aliases: [blog-post, social-post]
    extractable: true
    expert_routing: false

  - name: event
    primitive: temporal
    path_prefixes:
      - marketing/events/
    aliases: [webinar, conference]
    extractable: true
    expert_routing: false

  # ── Compliance ──
  - name: audit
    primitive: temporal
    path_prefixes:
      - compliance/audits/
    aliases: [assessment]
    extractable: true
    expert_routing: false

  - name: control
    primitive: concept
    path_prefixes:
      - compliance/controls/
    aliases: [security-control]
    extractable: true
    expert_routing: false

  - name: risk
    primitive: concept
    path_prefixes:
      - compliance/risks/
    aliases: [risk-register]
    extractable: true
    expert_routing: false

  # ── Engineering ──
  - name: adr
    primitive: media
    path_prefixes:
      - engineering/adrs/
    aliases: [architecture-decision]
    extractable: true
    expert_routing: false

  - name: codebase
    primitive: entity
    path_prefixes:
      - engineering/codebases/
    aliases: [repo, repository]
    extractable: true
    expert_routing: true

  - name: deployment
    primitive: temporal
    path_prefixes:
      - engineering/deployments/
    aliases: [deploy, release-deploy]
    extractable: true
    expert_routing: false

  # ── Support ──
  - name: kb-article
    primitive: media
    path_prefixes:
      - support/kb/
    aliases: [knowledge-base, help-article]
    extractable: true
    expert_routing: false

  - name: customer
    primitive: entity
    path_prefixes:
      - support/customers/
    aliases: [client]
    extractable: true
    expert_routing: true

link_types:
  - verb: assigned_to
    from_types: [ticket, leave-request, milestone]
    to_types: [staff]

  - verb: reports_to
    from_types: [staff]
    to_types: [staff]

  - verb: manages
    from_types: [staff]
    to_types: [budget, project]

  - verb: belongs_to
    from_types: [expense, invoice]
    to_types: [budget]

  - verb: raised_by
    from_types: [ticket]
    to_types: [customer, staff]

  - verb: contacts_at
    from_types: [deal]
    to_types: [contact, company]

  - verb: ordered_from
    from_types: [purchase-order]
    to_types: [vendor]

  - verb: covers
    from_types: [contract]
    to_types: [vendor, project]

  - verb: ships_with
    from_types: [release]
    to_types: [prd, codebase]

  - verb: documents
    from_types: [adr, kb-article]
    to_types: [codebase, control]

  - verb: mitigates
    from_types: [control]
    to_types: [risk]

  - verb: audits
    from_types: [audit]
    to_types: [control, policy]

  - verb: promotes
    from_types: [campaign]
    to_types: [prd, event]

  - verb: references
    from_types: [content, prd]
    to_types: [roadmap, release]

frontmatter_links:
  - field: assignee
    verb: assigned_to
  - field: manager
    verb: reports_to
  - field: vendor
    verb: ordered_from
  - field: customer
    verb: raised_by
  - field: contact
    verb: contacts_at
  - field: budget
    verb: belongs_to
  - field: project
    verb: manages

enrichable_types:
  - company
  - contact
  - vendor
  - customer
  - staff

filing_rules: []
```

**Step 3: Validate the pack**

```bash
gbrain schema validate shogun-enterprise
```

**Step 4: Lint the pack**

```bash
gbrain schema lint shogun-enterprise
```

**Step 5: Activate the pack**

```bash
gbrain schema use shogun-enterprise
```

**Step 6: Verify activation**

```bash
gbrain schema active
```

**Step 7: Commit**

```bash
git add ~/.gbrain/schema-packs/shogun-enterprise/
git commit -m "feat: create shogun-enterprise schema pack with 30+ department types"
```

---

## Task 4: Wire Dream Cycle as Nightly Cron

**Objective:** Schedule the gbrain dream cycle (consolidate + synthesize + patterns) to run nightly at 2am.

**Context:** The dream cycle runs three phases:
1. **Consolidate** — merge duplicate facts, resolve contradictions
2. **Synthesize** — generate cross-page insights
3. **Patterns** — detect anomalies, drift

**Files:**
- Create: `scripts/gbrain-dream-cron.sh`

**Step 1: Create the cron wrapper script**

Create `scripts/gbrain-dream-cron.sh`:

```bash
#!/usr/bin/env bash
# Shogun OS — GBrain Dream Cycle (Nightly 2am)
# Runs: consolidate → synthesize → patterns
# Logs to: ~/.gbrain/logs/dream-YYYYMMDD.log

set -euo pipefail

GBRAIN_BIN="${GBRAIN_BIN:-$(which gbrain 2>/dev/null || echo "$HOME/.bun/bin/gbrain")}"
LOG_DIR="$HOME/.gbrain/logs"
LOG_FILE="$LOG_DIR/dream-$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

echo "=== GBrain Dream Cycle — $(date) ===" >> "$LOG_FILE"

# Phase 1: Consolidate
echo "[1/3] Consolidating facts..." >> "$LOG_FILE"
if "$GBRAIN_BIN" autopilot cycle --phase consolidate --yes >> "$LOG_FILE" 2>&1; then
  echo "[1/3] ✅ Consolidate complete" >> "$LOG_FILE"
else
  echo "[1/3] ❌ Consolidate failed" >> "$LOG_FILE"
fi

# Phase 2: Synthesize
echo "[2/3] Synthesizing..." >> "$LOG_FILE"
if "$GBRAIN_BIN" autopilot cycle --phase synthesize --yes >> "$LOG_FILE" 2>&1; then
  echo "[2/3] ✅ Synthesize complete" >> "$LOG_FILE"
else
  echo "[2/3] ❌ Synthesize failed" >> "$LOG_FILE"
fi

# Phase 3: Patterns
echo "[3/3] Detecting patterns..." >> "$LOG_FILE"
if "$GBRAIN_BIN" autopilot cycle --phase patterns --yes >> "$LOG_FILE" 2>&1; then
  echo "[3/3] ✅ Patterns complete" >> "$LOG_FILE"
else
  echo "[3/3] ❌ Patterns failed" >> "$LOG_FILE"
fi

echo "=== Dream cycle finished — $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
```

**Step 2: Make executable**

```bash
chmod +x scripts/gbrain-dream-cron.sh
```

**Step 3: Test manually**

```bash
./scripts/gbrain-dream-cron.sh
cat ~/.gbrain/logs/dream-$(date +%Y%m%d).log
```

**Step 4: Install as system cron**

```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * $HOME/shogun-os/scripts/gbrain-dream-cron.sh") | crontab -
```

**Step 5: Verify cron entry**

```bash
crontab -l | grep dream
```

**Step 6: Commit**

```bash
git add scripts/gbrain-dream-cron.sh
git commit -m "feat: add nightly dream cycle cron at 2am"
```

---

## Task 5: Add pg_dump Backup Script

**Objective:** Nightly pg_dump of the gbrain database. Git push is stubbed for future configuration.

**Files:**
- Create: `scripts/gbrain-backup.sh`

**Step 1: Create the backup script**

Create `scripts/gbrain-backup.sh`:

```bash
#!/usr/bin/env bash
# Shogun OS — GBrain Database Backup
# pg_dump to local file. Git push to remote is TODO (configure later).
# Logs to: ~/.gbrain/logs/backup-YYYYMMDD.log

set -euo pipefail

BACKUP_DIR="${GBRAIN_BACKUP_DIR:-$HOME/backups/gbrain}"
LOG_DIR="$HOME/.gbrain/logs"
LOG_FILE="$LOG_DIR/backup-$(date +%Y%m%d).log"
RETENTION_DAYS="${GBRAIN_BACKUP_RETENTION:-7}"

DB_NAME="${GBRAIN_DB_NAME:-gbrain}"
DB_USER="${GBRAIN_DB_USER:-gbrain}"
DB_HOST="${GBRAIN_DB_HOST:-127.0.0.1}"
DB_PORT="${GBRAIN_DB_PORT:-5432}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/gbrain_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR" "$LOG_DIR"

echo "=== GBrain Backup — $(date) ===" >> "$LOG_FILE"

# Dump
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --no-password --clean --if-exists | gzip > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
  SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  echo "✅ Backup created: $BACKUP_FILE ($SIZE)" >> "$LOG_FILE"
else
  echo "❌ Backup failed" >> "$LOG_FILE"
  exit 1
fi

# Prune old backups
find "$BACKUP_DIR" -name "gbrain_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete 2>> "$LOG_FILE"
echo "🧹 Pruned backups older than $RETENTION_DAYS days" >> "$LOG_FILE"

# TODO: Git push to remote (configure later)
# Uncomment and configure when ready:
#
# GIT_DIR="$BACKUP_DIR/.git"
# if [ ! -d "$GIT_DIR" ]; then
#   git -C "$BACKUP_DIR" init
#   git -C "$BACKUP_DIR" remote add origin <your-backup-repo-url>
# fi
# git -C "$BACKUP_DIR" add -A
# git -C "$BACKUP_DIR" commit -m "backup: $TIMESTAMP"
# git -C "$BACKUP_DIR" push origin main

echo "=== Backup finished — $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
```

**Step 2: Make executable**

```bash
chmod +x scripts/gbrain-backup.sh
```

**Step 3: Test**

```bash
./scripts/gbrain-backup.sh
cat ~/.gbrain/logs/backup-$(date +%Y%m%d).log
ls -lh ~/backups/gbrain/
```

**Step 4: Add to crontab (after dream cycle, 2:30am)**

```bash
(crontab -l 2>/dev/null; echo "30 2 * * * $HOME/shogun-os/scripts/gbrain-backup.sh") | crontab -
```

**Step 5: Commit**

```bash
git add scripts/gbrain-backup.sh
git commit -m "feat: add nightly pg_dump backup at 2:30am (git push stubbed)"
```

---

## Task 6: Configure HTTP MCP Transport for Web Portal

**Objective:** Start a persistent gbrain HTTP MCP server for the Shogun web portal to query.

**Context:** Profiles use stdio MCP (current). The web portal needs HTTP MCP with OAuth 2.1. gbrain supports `gbrain serve --http --port N`.

**Files:**
- Create: `scripts/gbrain-http-service.sh`
- Modify: `shogun-web/server/config.py` (add gbrain HTTP endpoint)

**Step 1: Create the HTTP service script**

Create `scripts/gbrain-http-service.sh`:

```bash
#!/usr/bin/env bash
# Shogun OS — GBrain HTTP MCP Server
# Serves the web portal via HTTP MCP with OAuth 2.1.
# Run as a background service (systemd or screen/tmux).

set -euo pipefail

GBRAIN_BIN="${GBRAIN_BIN:-$(which gbrain 2>/dev/null || echo "$HOME/.bun/bin/gbrain")}"
GBRAIN_HTTP_PORT="${GBRAIN_HTTP_PORT:-3100}"
GBRAIN_HTTP_HOST="${GBRAIN_HTTP_HOST:-127.0.0.1}"

echo "Starting GBrain HTTP MCP on $GBRAIN_HTTP_HOST:$GBRAIN_HTTP_PORT"
exec "$GBRAIN_BIN" serve --http --port "$GBRAIN_HTTP_PORT" --host "$GBRAIN_HTTP_HOST"
```

**Step 2: Make executable**

```bash
chmod +x scripts/gbrain-http-service.sh
```

**Step 3: Test the HTTP server**

```bash
# Start in background for testing
./scripts/gbrain-http-service.sh &
sleep 2
curl -s http://127.0.0.1:3100/health || echo "Health check endpoint TBD"
kill %1
```

**Step 4: Create systemd service (optional, for production)**

Create `/etc/systemd/system/gbrain-http.service`:

```ini
[Unit]
Description=GBrain HTTP MCP Server
After=postgresql.service ollama.service

[Service]
Type=simple
User=cheehow
Environment=GBRAIN_HTTP_PORT=3100
ExecStart=%h/shogun-os/scripts/gbrain-http-service.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable gbrain-http
sudo systemctl start gbrain-http
```

**Step 5: Update web portal config**

Add to `shogun-web/server/config.py`:

```python
# GBrain HTTP MCP endpoint for web portal queries
GBRAIN_HTTP_URL = os.environ.get("GBRAIN_HTTP_URL", "http://127.0.0.1:3100")
GBRAIN_HTTP_TOKEN = os.environ.get("GBRAIN_HTTP_TOKEN", "")  # OAuth 2.1 token
```

**Step 6: Commit**

```bash
git add scripts/gbrain-http-service.sh shogun-web/server/config.py
git commit -m "feat: add HTTP MCP transport for web portal (port 3100)"
```

---

## Task 7: Auto-Install PostgreSQL in init-gbrain.sh

**Objective:** The init script should auto-detect and install PostgreSQL if not present.

**Files:**
- Modify: `scripts/init-gbrain.sh` (add PG installation step)

**Step 1: Add PostgreSQL check + install to init-gbrain.sh**

Insert after the gbrain version check, before sources creation:

```bash
# ── PostgreSQL Check + Install ─────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ PostgreSQL Check ━━━${NC}"

if command -v psql &> /dev/null; then
  PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
  ok "PostgreSQL $PG_VERSION found"
else
  info "PostgreSQL not found. Installing..."
  if [[ "$DRY_RUN" == true ]]; then
    ok "[DRY-RUN] Would install PostgreSQL 16"
  else
    sudo apt-get update -qq
    sudo apt-get install -y -qq postgresql-16 postgresql-contrib-16
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
    ok "PostgreSQL 16 installed and started"
  fi
fi

# Ensure pgvector extension
if [[ "$DRY_RUN" != true ]]; then
  if sudo -u postgres psql -d gbrain -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
    ok "pgvector extension enabled"
  else
    info "pgvector will be created on first gbrain init"
  fi
fi

# Create gbrain database + user if they don't exist
if [[ "$DRY_RUN" != true ]]; then
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='gbrain'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER gbrain WITH PASSWORD 'gbrain';"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='gbrain'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE gbrain OWNER gbrain;"
  sudo -u postgres psql -d gbrain -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
  ok "gbrain database + user ready"
fi
```

**Step 2: Test the modified script in dry-run**

```bash
./scripts/init-gbrain.sh --dry-run
```

**Step 3: Commit**

```bash
git add scripts/init-gbrain.sh
git commit -m "feat: auto-install PostgreSQL 16 + pgvector in init-gbrain.sh"
```

---

## Task 8: PGLite → Postgres Migration Path

**Objective:** For existing installs that started with PGLite, provide a one-command migration to local Postgres.

**Context:** `gbrain migrate --to supabase` works for Supabase. For self-hosted local Postgres, the same command works with `--url`.

**Files:**
- Create: `scripts/gbrain-migrate-pglite-to-postgres.sh`

**Step 1: Create the migration script**

Create `scripts/gbrain-migrate-pglite-to-postgres.sh`:

```bash
#!/usr/bin/env bash
# Shogun OS — Migrate GBrain from PGLite to Local Postgres
# For existing installs that started with PGLite (zero-config default).
# Safe: creates a full export before switching.

set -euo pipefail

GBRAIN_BIN="${GBRAIN_BIN:-$(which gbrain 2>/dev/null || echo "$HOME/.bun/bin/gbrain")}"
PG_HOST="${GBRAIN_DB_HOST:-127.0.0.1}"
PG_PORT="${GBRAIN_DB_PORT:-5432}"
PG_USER="${GBRAIN_DB_USER:-gbrain}"
PG_NAME="${GBRAIN_DB_NAME:-gbrain}"
PG_URL="postgresql://${PG_USER}@${PG_HOST}:${PG_PORT}/${PG_NAME}"

BACKUP_DIR="$HOME/backups/gbrain-pre-migration"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()    { echo -e "  ${GREEN}✅${NC} $1"; }
info()  { echo -e "  ${CYAN}💡${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠️${NC} $1"; }
err()   { echo -e "  ${RED}❌${NC} $1"; }

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  GBrain PGLite → Postgres Migration${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

# Check current engine
CURRENT_ENGINE=$("$GBRAIN_BIN" config get engine 2>/dev/null || echo "unknown")
info "Current engine: $CURRENT_ENGINE"

if [[ "$CURRENT_ENGINE" == "postgres" ]]; then
  ok "Already on Postgres. Nothing to do."
  exit 0
fi

# Check Postgres is running
if ! pg_isready -h "$PG_HOST" -p "$PG_PORT" -q 2>/dev/null; then
  err "PostgreSQL not reachable at $PG_HOST:$PG_PORT"
  info "Run: sudo systemctl start postgresql"
  exit 1
fi
ok "PostgreSQL reachable at $PG_HOST:$PG_PORT"

# Backup current PGLite data
info "Backing up PGLite data..."
mkdir -p "$BACKUP_DIR"
cp -r "$HOME/.gbrain" "$BACKUP_DIR/gbrain_${TIMESTAMP}/"
ok "Backup saved to $BACKUP_DIR/gbrain_${TIMESTAMP}/"

# Ensure pgvector
sudo -u postgres psql -d "$PG_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

# Run migration
info "Running migration..."
echo ""

if "$GBRAIN_BIN" migrate --to supabase --url "$PG_URL" --force; then
  echo ""
  ok "Migration complete!"
  info "Engine: $("$GBRAIN_BIN" config get engine 2>/dev/null)"
  info "Database: $PG_URL"
else
  echo ""
  err "Migration failed. Restore from backup:"
  err "  cp -r $BACKUP_DIR/gbrain_${TIMESTAMP}/ $HOME/.gbrain/"
  exit 1
fi

# Verify
echo ""
info "Verifying..."
"$GBRAIN_BIN" doctor 2>&1 | head -10 || true
"$GBRAIN_BIN" stats 2>&1 || true

echo ""
ok "Migration verified. PGLite backup preserved at $BACKUP_DIR/gbrain_${TIMESTAMP}/"
```

**Step 2: Make executable**

```bash
chmod +x scripts/gbrain-migrate-pglite-to-postgres.sh
```

**Step 3: Commit**

```bash
git add scripts/gbrain-migrate-pglite-to-postgres.sh
git commit -m "feat: add PGLite → Postgres migration script with backup"
```

---

## Task 9: Update init-gbrain.sh with All New Steps

**Objective:** Integrate Ollama check, embedding config, schema pack activation, and cron setup into the main init script.

**Files:**
- Modify: `scripts/init-gbrain.sh` (add post-source steps)

**Step 1: Add Ollama + embedding configuration**

Add after the "Model Tier Configuration" section:

```bash
# ── Ollama + Local Embedding ─────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Local Embedding (Ollama) ━━━${NC}"

if command -v ollama &> /dev/null; then
  ok "Ollama found: $(ollama --version 2>/dev/null || echo 'installed')"

  # Check if nomic-embed-text is pulled
  if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    ok "nomic-embed-text model available"
  else
    info "Pulling nomic-embed-text embedding model..."
    if [[ "$DRY_RUN" != true ]]; then
      ollama pull nomic-embed-text
      ok "nomic-embed-text pulled"
    else
      ok "[DRY-RUN] Would pull nomic-embed-text"
    fi
  fi

  # Set embedding provider if not already set to ollama
  CURRENT_EMB=$("$GBRAIN_BIN" config get embedding_model 2>/dev/null || echo "")
  if [[ "$CURRENT_EMB" != *"ollama"* ]]; then
    if [[ "$DRY_RUN" != true ]]; then
      "$GBRAIN_BIN" config set embedding_model "ollama:nomic-embed-text" 2>/dev/null || true
      "$GBRAIN_BIN" config set embedding_dimensions "768" 2>/dev/null || true
      ok "Embedding → ollama:nomic-embed-text (768d)"
    else
      ok "[DRY-RUN] Would set embedding → ollama:nomic-embed-text"
    fi
  else
    ok "Embedding already set to: $CURRENT_EMB"
  fi
else
  warn "Ollama not found — skipping local embedding setup"
  info "Install: curl -fsSL https://ollama.com/install.sh | sh"
fi

# ── Schema Pack ───────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Schema Pack ━━━${NC}"

SCHEMA_PACK_DIR="$HOME/.gbrain/schema-packs/shogun-enterprise"
if [[ -d "$SCHEMA_PACK_DIR" ]]; then
  ok "shogun-enterprise pack found"
  if [[ "$DRY_RUN" != true ]]; then
    "$GBRAIN_BIN" schema use shogun-enterprise 2>/dev/null && \
      ok "Schema pack → shogun-enterprise" || \
      warn "Failed to activate shogun-enterprise pack"
  else
    ok "[DRY-RUN] Would activate shogun-enterprise"
  fi
else
  info "shogun-enterprise pack not found at $SCHEMA_PACK_DIR"
  info "Create it: gbrain schema init shogun-enterprise"
fi

# ── Cron Setup ────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}━━━ Cron Setup ━━━${NC}"

if [[ "$DRY_RUN" != true ]]; then
  # Dream cycle
  if ! crontab -l 2>/dev/null | grep -q "gbrain-dream-cron"; then
    (crontab -l 2>/dev/null; echo "0 2 * * * $HOME/shogun-os/scripts/gbrain-dream-cron.sh") | crontab -
    ok "Cron: dream cycle nightly at 2:00am"
  else
    ok "Cron: dream cycle already scheduled"
  fi

  # Backup
  if ! crontab -l 2>/dev/null | grep -q "gbrain-backup"; then
    (crontab -l 2>/dev/null; echo "30 2 * * * $HOME/shogun-os/scripts/gbrain-backup.sh") | crontab -
    ok "Cron: pg_dump backup nightly at 2:30am"
  else
    ok "Cron: backup already scheduled"
  fi
else
  ok "[DRY-RUN] Would install dream cycle + backup crons"
fi
```

**Step 2: Test in dry-run**

```bash
./scripts/init-gbrain.sh --dry-run
```

**Step 3: Commit**

```bash
git add scripts/init-gbrain.sh
git commit -m "feat: integrate Ollama, schema pack, and cron setup into init-gbrain.sh"
```

---

## Task 10: Update ARCHITECTURE.md + Docs

**Objective:** Reflect the new GBrain integration in the architecture doc.

**Files:**
- Modify: `ARCHITECTURE.md` (update Layer 2 section)
- Modify: `SETUP.md` (add GBrain setup steps)
- Modify: `CHANGELOG.md` (add v3.11.0 entry)

**Step 1: Update ARCHITECTURE.md Layer 2 section**

Replace the GBrain section with:

```markdown
### Layer 2: GBrain (Knowledge Layer)

Every profile connects to gbrain via MCP. The brain architecture:

\`\`\`
gbrain sources/
├── shared/          ← Federated read, write restricted to HR
├── hr/
├── finance/
├── projects/
├── procurement/
├── products/
├── crm/
├── marketing/
├── compliance/
├── engineering/
└── support/
\`\`\`

**Engine:** Local PostgreSQL 16 with pgvector. Zero external dependency.

**Embedding:** Ollama `nomic-embed-text` (768d, local, $0 cost). No API key needed.

**Schema Pack:** `shogun-enterprise` — 30+ department-specific page types with expert routing, link inference, and extraction rules.

**Federated read:** Every profile can read from `shared/` (staff directory, company policies, taxonomy). Writes go to the profile's own source.

**Hybrid search:** pgvector + tsvector via Postgres. Semantic + keyword search with RRF fusion.

**MCP Transport:**
- **stdio** — per-profile MCP servers (default, zero network overhead)
- **HTTP** — shared HTTP MCP on port 3100 for web portal queries

**Nightly maintenance:**
- **2:00am** — Dream cycle (consolidate facts, synthesize insights, detect patterns)
- **2:30am** — pg_dump backup to `~/backups/gbrain/` (7-day retention)
```

**Step 2: Update CHANGELOG.md**

Add:

```markdown
### v3.11.0 — GBrain Production Integration
- **Local embeddings** — Ollama nomic-embed-text (768d, $0 cost, no API keys)
- **Local Postgres 16** — auto-install with pgvector in init-gbrain.sh
- **shogun-enterprise schema pack** — 30+ department page types, link verbs, expert routing
- **Dual MCP transport** — stdio for profiles, HTTP for web portal (port 3100)
- **Nightly dream cycle** — 2am consolidate + synthesize + patterns
- **pg_dump backups** — 2:30am nightly with 7-day retention (git push TODO)
- **PGLite migration** — one-command migration script for existing installs
```

**Step 3: Commit**

```bash
git add ARCHITECTURE.md SETUP.md CHANGELOG.md
git commit -m "docs: update architecture for GBrain production integration"
```

---

## Execution Order

| Phase | Tasks | Dependencies |
|-------|-------|-------------|
| 1 | Task 1 (Ollama install) | None |
| 2 | Task 7 (PG auto-install) + Task 3 (schema pack) | Task 1 |
| 3 | Task 2 (embedding migration) | Task 1 (Ollama must be running) |
| 4 | Task 4 (dream cron) + Task 5 (backup) + Task 6 (HTTP MCP) | Task 2 |
| 5 | Task 8 (PGLite migration) + Task 9 (init script) + Task 10 (docs) | All above |

**Critical path:** Task 1 → Task 2 (embedding migration is the longest-running task)

---

## Verification Checklist

After all tasks complete:

```bash
# 1. Ollama serving embeddings
curl -s http://localhost:11434/api/tags | grep nomic

# 2. Postgres running + gbrain database
pg_isready -h 127.0.0.1 -p 5432
sudo -u postgres psql -d gbrain -c "SELECT count(*) FROM pages;"

# 3. Embedding provider is Ollama
gbrain config get embedding_model
# Expected: ollama:nomic-embed-text

# 4. Schema pack active
gbrain schema active
# Expected: shogun-enterprise

# 5. Sources exist
gbrain sources list
# Expected: 11 sources (shared + 10 departments)

# 6. Federated read
gbrain sources list | grep shared
# Expected: shared = federated

# 7. Dream cycle cron
crontab -l | grep dream
# Expected: 0 2 * * *

# 8. Backup cron
crontab -l | grep backup
# Expected: 30 2 * * *

# 9. HTTP MCP running (if systemd)
systemctl status gbrain-http

# 10. Search quality
gbrain query "test" --limit 3

# 11. Doctor health
gbrain doctor
```

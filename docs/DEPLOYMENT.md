# Deployment Guide — Shogun OS

## Environment Overview

| Environment | Target Platform | Description |
|---|---|---|
| **Development** | Local Windows / WSL (Ubuntu) | Profile creation, script testing (`--dry-run`), skill development |
| **Staging** | Staging Linux Server / Docker | Full Hermes Agent daemon, GBrain PostgreSQL, test Slack/Telegram bot |
| **Production** | Dedicated Production Linux Node | 10 active department gateways, live provider APIs, production crons |

---

## Prerequisites

### System Requirements
- **OS:** Linux (Ubuntu 22.04 LTS recommended) or WSL2 on Windows
- **Python:** 3.10+ (with `pyyaml`, `requests`, `python-dotenv`)
- **Node.js / Bun:** Node 18+ or Bun (for GBrain CLI & Web Portal frontend)
- **PostgreSQL:** 16+ with `pgvector` extension (for GBrain hybrid search)
- **Ollama:** Local instance running `nomic-embed-text` (for 768d embeddings)
- **Hermes Agent CLI:** `hermes` CLI (v0.19.0+) installed and accessible in system `PATH`

---

## Environment Variables

Configure per-profile environment variables in `~/.hermes/profiles/<profile-name>/.env`:

| Variable | Required | Default | Description |
|---|---|---|---|
| `GBRAIN_SOURCE` | Yes | `finance/` | Primary GBrain write source for the profile |
| `GBRAIN_FEDERATED_READ` | Yes | `true` | Enables read access to `shared/` knowledge source |
| `OPENAI_API_KEY` | Optional* | — | OpenAI API key (or set up via `hermes setup model`) |
| `ANTHROPIC_API_KEY` | Optional* | — | Anthropic API key |
| `SLACK_BOT_TOKEN` | Optional | — | Bot token (`xoxb-...`) for Slack delivery |
| `SLACK_APP_TOKEN` | Optional | — | App-level token (`xapp-...`) for Socket Mode |
| `TELEGRAM_BOT_TOKEN` | Optional | — | Telegram Bot API token |
| `ACCOUNTING_PROVIDER` | Optional | `quickbooks` | Active provider for `acct_*` contract (`quickbooks`, `bukku`, `xero`) |

*\* At least one valid LLM provider API key or local Ollama configuration is required.*

---

## Step-by-Step Provisioning Guide

### Step 1: Provision GBrain Knowledge Base
Initialize the PostgreSQL vector store and create the 11 department sources:

```bash
# Provision GBrain sources and schema pack
./scripts/init-gbrain.sh
```

---

### Step 2: Generate Department Profile (`finance-manager`)
Run `generate-profile.py` to construct the Hermes profile directory, link skills, copy `scrum.yaml`, and seed `budget.json`:

```bash
# Generate finance-manager profile (force overwrites existing config safely)
python3 scripts/generate-profile.py finance-manager --type finance --force
```

**Verification:**
Verify that the profile directory was populated cleanly:
```bash
ls -la ~/.hermes/profiles/finance-manager/
ls -la ~/.hermes/profiles/finance-manager/skills/
```

---

### Step 3: Wire Department Cron Jobs
Register the 4 department scrum crons and 4 domain crons into Hermes:

```bash
# Dry-run check first
python3 scripts/wire-crons.py finance-manager --type finance --dry-run

# Apply crons to the profile
python3 scripts/wire-crons.py finance-manager --type finance --apply
```

**Verification:**
Check active cron schedules in Hermes:
```bash
hermes -p finance-manager cron list
```

---

### Step 4: Run the Profile Gateway Daemon
Start the Hermes HTTP Gateway daemon for `finance-manager` on port `8006` (or `9102`):

```bash
# Start profile gateway
hermes serve --profile finance-manager --port 8006
```

---

## Health Check & Verification

### 1. Offline Script Verification (Dry-Run Mode)
Verify report generator logic without needing live API credentials or LLM tokens:

```bash
# 1. Weekly Pulse Report
python3 skills/finance/weekly-pulse-report/scripts/weekly_pulse.py --dry-run

# 2. Monthly Board Report
python3 skills/finance/monthly-board-report/scripts/monthly_board.py --dry-run

# 3. BvA Variance Analysis Engine
python3 skills/finance/bva-variance-analysis/scripts/variance.py \
  --budget examples/finance-budget.json \
  --actuals skills/finance/monthly-board-report/scripts/monthly_board.py
```

### 2. Full System Verification Suite
Run the automated Shogun OS verification suite:

```bash
# Quick verification
./scripts/verify-install.sh --quick

# Full verification (includes MCP connectivity and skill audits)
./scripts/verify-install.sh
```

---

## Troubleshooting & Common Issues

| Symptom | Likely Cause | Solution |
|---|---|---|
| `'hermes' CLI not found` | Hermes CLI not installed on host `PATH` | Install Hermes CLI via `curl -fsSL https://hermes.nousresearch.com/install.sh \| bash` or test via WSL/Linux server. |
| `Unknown provider 'openai'` | Missing LLM provider configuration | Run `hermes setup model` or add `OPENAI_API_KEY="..."` to `~/.hermes/profiles/finance-manager/.env`. |
| `UnicodeEncodeError` on Windows | `cp1252` console encoding failure on emojis | Python scripts automatically wrap `sys.stdout` in UTF-8. Ensure `PYTHONIOENCODING=utf-8` environment variable is set. |
| `Budget baseline (budget.json) missing` | `budget.json` missing from profile folder | Re-run `python3 scripts/generate-profile.py finance-manager --type finance --force` to seed `budget.json`. |
| `Gateway is not running` | Hermes daemon not running in background | Start gateway via `hermes serve --profile finance-manager --port 8006` or install background service via `hermes gateway install`. |

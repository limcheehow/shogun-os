# Shogun OS — Install Protocol for AI Agents

> **An AI agent should be able to read this file and deploy Shogun OS on a fresh Hermes install without human intervention, except where API keys or Slack tokens must be provided.**

## Prerequisites

Before starting, verify:

```bash
which hermes          # Hermes Agent v0.x+ installed
hermes --version
which gbrain          # GBrain v0.42.x+ installed
gbrain --version
```

If either is missing, install:
```bash
# Hermes Agent
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# GBrain (via Bun)
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"
bun install -g github:garrytan/gbrain
```

**STOP** if either command fails. The installer will need the user's system password for Hermes installation.

---

## Phase 1: Clone and Install

```bash
git clone https://github.com/limcheehow/shogun-os.git
cd company-os
./scripts/install.sh
```

Install.sh will:
1. Copy all 6 skills to `~/.hermes/skills/`
2. Copy all scripts to `~/.hermes/scripts/`
3. Copy config files (gmail-batches.json, scrum config example)
4. Check gbrain version (recommends v0.42.x+)
5. Create SA-DWD symlink if service account key exists

Show the summary to the user.

---

## Phase 2: Ask for API Keys

Shogun OS needs these secrets. Collect them from the user before proceeding:

| Key | Where to get it |
|-----|----------------|
| `DASHSCOPE_API_KEY` | Alibaba Cloud Primary Provider console (for deepseek-v4-flash) |
| `OPENROUTER_API_KEY` | Backup Provider dashboard (fallback provider) |
| `SUPABASE_URL` | Supabase project settings (for gbrain) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase project settings |
| `TELEGRAM_BOT_TOKEN` | BotFather on Telegram (if using Telegram gateway) |

For each Slack bot (one per department), the user needs:
- **Bot User OAuth Token** (`xoxb-...`) — from Slack App settings → OAuth & Permissions
- **App-Level Token** (`xapp-...`) — from Slack App settings → App-Level Tokens

Write secrets to `~/.hermes/.env`:
```bash
cat >> ~/.hermes/.env << 'EOF'
DASHSCOPE_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
EOF
```

---

## Phase 3: Initialize GBrain

```bash
./scripts/init-gbrain.sh --yes
```

This creates 11 gbrain sources:
| Source | Purpose |
|--------|---------|
| `shared` | Staff directory, policies, taxonomy (federated read) |
| `hr` | HR operations, leave, recruitment |
| `finance` | Budgets, revenue, expenses |
| `projects` | Project delivery, milestones |
| `procurement` | POs, vendors, contracts |
| `products` | PRDs, roadmaps, releases |
| `crm` | Deals, companies, contacts |
| `marketing` | Campaigns, content, brand |
| `compliance` | Policies, audits, controls |
| `engineering` | Codebases, ADRs, deployments |
| `support` | Tickets, KB articles, customers |

**STOP** — verify sources exist:
```bash
gbrain list-sources
```

---

## Phase 4: Deploy Profiles

```bash
./scripts/install.sh --deploy all
```

This creates 10 Hermes Agent profiles with SOUL.md, config.yaml, and .env stubs:

| Profile | Type | Persona | gbrain Source |
|---------|------|---------|--------------|
| coding-agent | coding | Takumi (匠) | engineering |
| hr-manager | hr | Jinzai (人材) | hr |
| finance-manager | finance | Koku (石) | finance |
| project-manager | project-manager | Gorobei (五郎兵衛) | projects |
| procurement-manager | procurement | Kura (蔵) | procurement |
| product-manager | product | Shi (志) | products |
| crm-manager | crm | Kizuna (絆) | crm |
| marketing-manager | marketing | Haiku (俳句) | marketing |
| compliance-manager | compliance | Kata (型) | compliance |
| customer-support | support | Bōei (防衛) | support |

**STOP** — verify profiles exist:
```bash
hermes profile list
```

---

## Phase 5: Configure Profiles

### 5.1 Add API Keys to Profile .env Files

Each profile has its own `.env` at `~/.hermes/profiles/<name>/.env` — profiles DO NOT inherit from main `.env`.

For each profile that needs a Slack bot, add:
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

For all profiles, add:
```bash
DASHSCOPE_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

### 5.2 Configure GBrain MCP

Each profile's config.yaml should have:
```yaml
mcp_servers:
  gbrain:
    command: gbrain
    args: [serve]
    env:
      GBRAIN_SOURCE: "<dept>"  # e.g., "hr" for hr-manager
      GBRAIN_FEDERATED_READ: "true"
```

This is auto-configured by `generate-profile.py`. Verify with:
```bash
hermes config show --profile hr-manager mcp_servers
```

### 5.3 Set Up Slack Bots

For each department that needs a Slack bot:

1. Go to https://api.slack.com/apps → Create New App
2. Choose "From an app manifest"
3. Set bot token scopes: `chat:write`, `channels:history`, `im:history`, `users:read`, `reactions:write`
4. Install to workspace — copy Bot User OAuth Token
5. Enable Socket Mode
6. Subscribe to bot events: `message.im`, `app_mention`
7. Add tokens to profile's .env
8. Enable Slack in profile's config.yaml:
   ```yaml
   slack:
     enabled: true
     allowed_channels: "C0B2NTXJD9U"
   ```
9. Invite bot to channels: `/invite @botname`

---

## Phase 6: Wire Cron Jobs

### 6.1 Infrastructure Crons (default profile)

```bash
python3 scripts/wire-crons.py base --type base --deliver local --apply
```

### 6.2 Department Scrum Crons

For each department profile, wire the 3-tier scrum workflow:

```bash
python3 scripts/wire-crons.py hr-manager --type hr --deliver "slack:<channel>" --apply
python3 scripts/wire-crons.py finance-manager --type finance --deliver "slack:<channel>" --apply
# ... repeat for each department
```

Options:
- `--list` — preview commands without running
- `--dry-run` — simulate creation
- `--apply` — create all cron jobs

### 6.3 Verify Crons

```bash
hermes cron list
```

---

## Phase 7: Verification

```bash
./scripts/verify-install.sh
```

Checks performed:
1. ✅ Skills installed (department-scrum, brain-ingest-pipeline, slack-formatting, brain-compliance, profile-enrichment, gbrain-operations)
2. ✅ Scripts installed (send-scrum-dms.py, gmail-triage.py, etc.)
3. ✅ Gmail batch config installed (valid JSON)
4. ✅ SA-DWD symlink exists
5. ✅ Hermes CLI available
6. ✅ Hermes recognizes all 6 skills
7. ✅ GBrain MCP configured and responding
8. ✅ stock-scanner MCP configured (optional)
9. ✅ Repo integrity (no old paths, no superseded recipes)

---

## Phase 8: Go Live

### 8.1 Start Slack Gateways

For each profile with a Slack bot:
```bash
hermes gateway start --profile <profile>
```

Verify each gateway:
```bash
hermes gateway status --profile <profile>
# Expected: running
```

### 8.2 Enable Cron Jobs

All cron jobs are created in `enabled: true` state. They fire on their next scheduled tick. To verify:
```bash
hermes cron list | grep -B 1 "enabled: false"
# Should return no results (all enabled)
```

### 8.3 Test a Profile

```bash
hermes -p hr-manager --exec "mcp_gbrain_whoami"
# Expected: your brain identity with hr source
```

### 8.4 Post-Install

- Check brain health: `gbrain doctor`
- Review SETUP.md for remaining configuration (Scrum configs, model switching)
- Import initial staff directory: `mkdir -p ~/brain/shared/staff && gbrain import ~/brain/shared/staff`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Profile already exists` | Use `--force` on generate-profile.py |
| `.env` not inherited | Each profile has its own `.env` — copy keys explicitly |
| Slack bot doesn't respond | Check `allowed_channels` in config.yaml, verify gateway is running |
| Scrum crons not firing | Verify `scrum.yaml` exists in profile directory with real channel IDs |
| gbrain MCP not found | Add to config.yaml: `mcp_servers.gbrain.command: gbrain` |
| No LLM provider | Profile `.env` missing API key — copy from main `~/.hermes/.env` |
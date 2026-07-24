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
cd shogun-os
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
| `SUPABASE_URL` | Supabase project settings (for gbrain) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase project settings |
| `TELEGRAM_BOT_TOKEN` | BotFather on Telegram (if using Telegram gateway) |

For each Slack bot (one per department), the user needs:
- **Bot User OAuth Token** (`xoxb-...`) — from Slack App settings → OAuth & Permissions
- **App-Level Token** (`xapp-...`) — from Slack App settings → App-Level Tokens

Write secrets to `~/.hermes/.env`:
```bash
cat >> ~/.hermes/.env << 'EOF'
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
gbrain sources list
```

---

## Phase 4: Deploy Profiles

```bash
./scripts/install.sh --deploy
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

### 5.1 Add Per-Profile Secrets

Each profile has its own `.env` at `~/.hermes/profiles/<name>/.env` — profiles DO NOT inherit from the main `.env`.

**Profiles use the default model config.** No per-profile API keys for the LLM provider are needed. The main `~/.hermes/.env` (or `~/.hermes/config.yaml` default profile) handles model configuration.

For each profile that needs a Slack bot, add:
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

### 5.2 Configure GBrain MCP

Each profile's config.yaml should have:
```yaml
mcp_servers:
  gbrain:
    command: gbrain
    args: [mcp]
```

This is auto-configured by `generate-profile.py` and `init-gbrain.sh` (they write `GBRAIN_SOURCE` and `GBRAIN_FEDERATED_READ` into each profile's `.env` and `config.yaml`). Verify with:
```bash
hermes -p hr-manager config show
```
Look for the `mcp_servers.gbrain.env` block with `GBRAIN_SOURCE: hr`.

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

> **Note:** On Windows, Hermes stores its home under
> `C:\Users\<you>\AppData\Local\hermes` (not `~/.hermes`). The wiring
> scripts resolve this automatically. Also use `python` (not `python3`),
> which is absent/unusable on this host.

### 6.1 Infrastructure Crons

Shogun OS does **not** wire infrastructure crons that depend on Slack or a
team roster unless those are configured. The shared GBrain sync and nightly
maintenance jobs are created directly via the Hermes CLI (`gbrain_live_sync.sh`,
`gbrain_nightly_dream.sh`) — see your existing cron list.

If you want the scrum/standup cadence for a profile (requires a populated
`scrum.yaml` and, for delivery, a Slack channel), run:
```bash
python scripts/wire-crons.py <profile> --type <type> --deliver local --apply
# e.g.
python scripts/wire-crons.py hr-manager --type hr --deliver local --apply
```

### 6.2 Verify Crons

```bash
hermes -p <profile> cron list
```

---

## Phase 7: Verification

```bash
./scripts/verify-install.sh
```

Checks performed (warnings are non-fatal — e.g. Google DWD ingest is optional):
1. ✅ Skills installed (21 skills)
2. ✅ Scripts installed (init-gbrain.sh, wire-crons.py, verify-install.sh, verify-comprehensive.py) — Python syntax validated
3. ⚠️ Gmail batch config (optional — only if Google DWD is set up)
4. ⚠️ SA-DWD key/symlink (optional — only if Google DWD is set up)
5. ✅ Hermes CLI available
6. ✅ Hermes recognizes key skills
7. ✅ GBrain MCP configured + connects (via `hermes -p <profile> mcp test`)
8. ⚠️ stock-scanner MCP (optional)
9. ✅ Repo integrity (no old paths, no superseded recipes)

The script exits non-zero only on hard failures (missing skills/scripts, syntax errors, repo regressions).

---

## Phase 8: Go Live

### 8.1 Start Slack Gateways (only if Slack bots are configured)

For each profile with a Slack bot:
```bash
hermes -p <profile> gateway start
```

Verify each gateway:
```bash
hermes -p <profile> gateway status
# Expected: running
```

> On Windows, gateways run under the Hermes Desktop app rather than systemd.
> Start them from the Hermes GUI or via the command above in a persistent session.

### 8.2 Enable Cron Jobs

All cron jobs are created in `enabled: true` state. They fire on their next scheduled tick. To verify:
```bash
hermes -p <profile> cron list
```

### 8.3 Test a Profile

```bash
hermes -p hr-manager -z "Call mcp_gbrain_whoami and report the result"
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
| gbrain MCP not found | Add to config.yaml: `mcp_servers.gbrain.command: gbrain`, `mcp_servers.gbrain.args: [mcp]` |
|| No LLM provider | Default profile config handles model settings — no per-profile API keys needed. Check `~/.hermes/config.yaml` model section |
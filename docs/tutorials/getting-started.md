# Getting Started with Company OS

> **From zero to your first working department agent in about 30 minutes.**

This tutorial walks through the first deployment end-to-end. By the end, you'll have a running AI agent for one department with its own knowledge base and Slack bot.

## What You'll Need

| Requirement | Details |
|------------|---------|
| A Linux/Mac/WSL machine | Any computer with terminal access |
| Hermes Agent installed | `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh \| bash` |
| A Supabase account | Free tier at [supabase.com](https://supabase.com) — for gbrain |
| A Slack workspace | Free tier — for the agent's Slack bot |
| API keys | Backup Provider or Primary Provider for the LLM |

## Step 1: Install Prerequisites

```bash
# Install Hermes Agent
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes --version

# Install Bun + GBrain
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"
bun install -g github:garrytan/gbrain
gbrain --version

# Verify both are available
which hermes && which gbrain
```

**Expected output:** Both commands return version numbers. If either fails, resolve before proceeding.

## Step 2: Clone Company OS

```bash
git clone https://github.com/limuser/company-os.git
cd company-os
```

## Step 3: Run the Installer

```bash
./scripts/install.sh
```

This installs:
- **6 skills** to `~/.hermes/skills/` (scrum, brain ops, formatting, compliance, enrichment, gbrain operations)
- **Scripts** to `~/.hermes/scripts/`
- **Config examples** to `~/.hermes/config/`
- Checks gbrain version

## Step 4: Set Up Your API Keys

Create or edit `~/.hermes/.env` with your LLM provider key:

```bash
# For Primary Provider (Alibaba Cloud) — recommended default
export DASHSCOPE_API_KEY="sk-your-key-here"

# For Backup Provider — fallback
export OPENROUTER_API_KEY="sk-or-your-key-here"
```

Test that your model works:
```bash
hermes chat -q "Hello, what model are you running?"
```

## Step 5: Initialize GBrain

```bash
./scripts/init-gbrain.sh --yes
```

This creates 11 gbrain sources. The default profile's brain is your starting point.

**Verify:**
```bash
gbrain list-sources
# Expected: shared, hr, finance, projects, procurement, products, crm,
#            marketing, compliance, engineering, support
```

## Step 6: Deploy Your First Department Profile

Let's deploy **project-manager** (Gorobei — the project execution agent):

```bash
# Deploy with the install script
./scripts/install.sh --deploy-profile project-manager --type project-manager
```

This creates:
- A Hermes profile at `~/.hermes/profiles/project-manager/`
- `config.yaml` with model config + gbrain MCP
- `SOUL.md` with Gorobei's Samurai persona

**Verify:**
```bash
hermes profile list | grep project-manager
ls ~/.hermes/profiles/project-manager/
# Expected: config.yaml, SOUL.md, .env
```

## Step 7: Create a Slack Bot (Optional — Skip for CLI-Only)

Your department agent can work through the terminal, but for team use, it needs a Slack bot.

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From an app manifest
2. Name it "Gorobei" and pick your workspace
3. Add bot token scopes: `chat:write`, `channels:history`, `im:history`, `users:read`
4. Install to workspace — copy the **Bot User OAuth Token** (starts with `xoxb-`)
5. Enable Socket Mode — copy the **App-Level Token** (starts with `xapp-`)
6. Subscribe to bot events: `message.im`, `app_mention`

Add tokens to the profile's `.env`:
```bash
cat >> ~/.hermes/profiles/project-manager/.env << 'EOF'
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_APP_TOKEN=xapp-your-token-here
DASHSCOPE_API_KEY=sk-your-key-here
EOF
```

Enable Slack in the profile's `config.yaml`:
```bash
cat >> ~/.hermes/profiles/project-manager/config.yaml << 'EOF'
slack:
  enabled: true
  allowed_channels: ""
EOF
```

Start the gateway:
```bash
hermes gateway start --profile project-manager
```

**Verify:**
```bash
hermes gateway status --profile project-manager
# Expected: running
```

Invite the bot to a channel: `/invite @Gorobei`

## Step 8: Wire Scrum Cron Jobs

The 3-tier daily scrum is the core workflow. Create the cron jobs:

```bash
python3 scripts/wire-crons.py project-manager \
  --type project-manager \
  --deliver "slack:C0XXXXXXXX" \
  --apply
```

**Verify:**
```bash
hermes cron list | grep scrum
# Expected: 3 jobs (9am, 11am, 5pm)
```

## Step 9: Test Your Department Agent

```bash
# Talk to the agent
hermes -p project-manager

# Ask a question
hermes -p project-manager --exec "Who am I and what do I do?"

# Check brain connectivity
hermes -p project-manager --exec "mcp_gbrain_get_health"
```

**Expected:** Gorobei responds with their Samurai persona, domain knowledge, and brain health stats.

## Step 10: Verify Everything

```bash
./scripts/verify-install.sh
```

## Next Steps

Once your first agent is running:

| Tutorial | What You'll Learn |
|----------|------------------|
| [Add a New Department](docs/tutorials/add-new-department.md) | Create another department agent from scratch |
| [Wire Scrum for Your Team](docs/tutorials/scrum-setup.md) | Configure team roster and scrum.yaml |
| [Model Configuration](SETUP.md#phase-6-model-configuration) | Switch between standard and coding model presets |
| [Set Up Google DWD](recipes/google-dwd.md) | Enable email and calendar ingest |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `hermes` not found | Reinstall: `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh \| bash` |
| `gbrain` not found | `bun install -g github:garrytan/gbrain` |
| Profile creation fails | `hermes profile create project-manager` first, then run generate-profile.py |
| Slack bot doesn't reply | Invite to channel: `/invite @Gorobei`. Check gateway: `hermes gateway status` |
| No LLM provider error | Add `DASHSCOPE_API_KEY` to profile's `.env` (profiles don't inherit main) |
| gbrain MCP not responding | Ensure gbrain is installed and `gbrain serve` works standalone |
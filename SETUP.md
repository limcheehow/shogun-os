# Setup Playbook

> End-to-end guide from zero to running profiles. Follow in order.

## Phase 0: Prerequisites

```bash
# Hermes Agent
pip install hermes-agent  # or your install method
hermes --version

# GBrain
curl -fsSL https://bun.sh/install | bash
bun install -g github:garrytan/gbrain
gbrain --version

# Tokscale (for AI spend tracking)
npm install -g tokscale

# Google Auth libraries
pip install google-auth google-api-python-client
```

## Phase 1: Google DWD (Foundation)

See [`recipes/google-dwd.md`](recipes/google-dwd.md) for the full playbook.

**Summary:**
1. Create service account in Google Cloud Console
2. Enable Domain-Wide Delegation in Google Workspace Admin Console
3. Download service account key to `~/.hermes/secrets/google-dwd-sa.json` (the brain ingest pipeline scripts also look for this at `~/.hermes/service-account-key.json` via symlink — create with `ln -sf ~/.hermes/secrets/google-dwd-sa.json ~/.hermes/service-account-key.json`)
4. Verify token generation

**Depends on:** Google Workspace admin access.

## Phase 2: GBrain Setup

### 2.1 Initialize Brain

```bash
gbrain init
# Choose: Postgres + pgvector via Supabase (recommended for >1000 files)
```

### 2.2 Create Sources

```bash
gbrain sources add shared
gbrain sources add hr
gbrain sources add finance
gbrain sources add projects
gbrain sources add procurement
gbrain sources add products
gbrain sources add crm
gbrain sources add marketing
gbrain sources add compliance
gbrain sources add engineering
gbrain sources add support
```

Each source becomes its own folder under `~/brain/`.

### 2.3 Configure Federated Read

In each profile's `config.yaml` (except HR, which owns `shared/`):

```bash
gbrain config set federated_read true
```

Or set the environment variable:

```bash
export GBRAIN_FEDERATED_READ=true
```

### 2.4 Import Staff Directory

```bash
mkdir -p ~/brain/shared/staff
# Create one page per employee with:
# ---
# type: person
# department: engineering
# role: Senior Developer
# ---
# ...person details...

gbrain import ~/brain/shared/staff --no-embed
gbrain embed --stale
```

## Phase 3: Profile Creation

### 3.1 Create Each Profile

For each department, create the Hermes profile:

```bash
hermes profile create <dept>-manager
```

Then apply the template:
- `SOUL.md` — persona definition
- `config.yaml` — model config + MCP servers + Slack connection
- `skills/` — domain skills (symlink shared skills)
- `cron/jobs/` — cron templates
- `memories/` — initial persisted facts

### 3.2 Symlink Shared Skills

```bash
cd ~/.hermes/profiles/<dept>-manager/skills
ln -sf ../../../../skills/shared ./shared
```

### 3.3 Wire GBrain MCP

In each profile's `config.yaml`:

```yaml
mcp_servers:
  gbrain:
    command: "gbrain"
    args: ["mcp"]
    env:
      GBRAIN_SOURCE: "<dept>"
      GBRAIN_FEDERATED_READ: "true"
      SUPABASE_URL: "${SUPABASE_URL}"
      SUPABASE_SERVICE_ROLE_KEY: "${SUPABASE_SERVICE_ROLE_KEY}"
```

## Phase 4: Slack Bot Configuration

### 4.1 Create Slack Apps

One Slack app per profile.

1. Go to https://api.slack.com/apps → Create New App
2. Choose "From an app manifest"
3. Set bot token scopes: `chat:write`, `channels:history`, `im:history`, `users:read`, `reactions:write`
4. Install to workspace — copy the Bot User OAuth Token
5. Enable Socket Mode (for event subscriptions)
6. Subscribe to bot events: `message.im`, `app_mention`

### 4.2 Configure Profile

In `config.yaml`:

```yaml
slack:
  bot_token: "xoxb-..."
  app_token: "xapp-..."
  signing_secret: "..."
```

### 4.3 Invite Bots to Channels

```bash
# Invite each bot to its department's Slack channels
# e.g., #hr-general for hr-manager, #project-alpha for project-manager
```

## Phase 5: Cron Jobs

### 5.1 Default Profile Infrastructure Crons

These run on the `default` profile (shared infrastructure):

```bash
# Email Collector (no_agent, every 30min)
hermes cron create --name "Email Collector" \
  --schedule "*/30 * * * *" --script email-collector.py --no-agent

# Email Enrichment (agent, 3x/day)
hermes cron create --name "Email Enrichment" \
  --schedule "0 9,13,17 * * 1-5" \
  --skills "gbrain-operations" --enabled-toolsets "terminal,file,search"

# Calendar Sync (no_agent, daily 6AM)
hermes cron create --name "Calendar Sync" \
  --schedule "0 6 * * *" --script calendar-sync.py --no-agent

# Calendar Attendee Enrichment (daily 8AM)
hermes cron create --name "Calendar Attendee Enrichment" \
  --schedule "0 8 * * *" \
  --skills "gbrain-operations" --enabled-toolsets "terminal,file,search"

# Drive Sync (no_agent, weekdays 12/16/20)
hermes cron create --name "Drive Sync" \
  --schedule "0 12,16,20 * * 1-5" --script drive-sync.py --no-agent

# Token Utilization (weekly Monday 8AM, no_agent)
hermes cron create --name "Token Utilization Report" \
  --schedule "0 8 * * 1" --script token-util-report.sh --no-agent
```

### 5.2 Department Scrum (3-Tier Workflow)

Each department profile uses the **3-tier scrum workflow** from `skills/department-scrum/`.

#### Prerequisites

Before wiring crons, you need:

1. **SOUL.md "Scrum DM Handling" section** — copy from `skills/department-scrum/references/soul-snippet.md`
2. **scrum.yaml** — create `~/.hermes/profiles/<profile>/scrum.yaml` (see `examples/scrum-configs/` and `skills/department-scrum/references/scrum-config-schema.md`)
3. **Generic scripts** — `send-scrum-dms.py` and `check-scrum-replies.py` at `~/.hermes/scripts/scrum/`

#### Wire 3 Crons Per Profile

```bash
# 9am — Send DMs (no_agent)
hermes cron create --name "<profile>-scrum-9am" \
  --schedule "0 9 * * 1-5" \
  --script "send-scrum-dms.py --profile <profile>" \
  --no-agent \
  --deliver "slack:<channel_updates>"

# 11am — Warn non-responders (agent)
hermes cron create --name "<profile>-scrum-11am" \
  --schedule "0 11 * * 1-5" \
  --prompt "Loaded skills: department-scrum, task-management, staff-lookup. STEP 1: Run check-scrum-replies.py warn --profile <profile>. STEP 2: Cross-ref against gbrain source: <source>. STEP 3: Post summary to slack:<channel_updates>." \
  --skills "department-scrum,task-management,staff-lookup" \
  --enabled-toolsets "terminal,file,web,search" \
  --deliver "slack:<channel_updates>"

# 5pm — Compliance report (agent)
hermes cron create --name "<profile>-scrum-5pm" \
  --schedule "0 17 * * 1-5" \
  --prompt "Loaded skills: department-scrum, task-management, staff-lookup. STEP 1: Run check-scrum-replies.py report --profile <profile>. STEP 2: Full brain cross-ref + SMART gates. STEP 3: Post enriched report." \
  --skills "department-scrum,task-management,staff-lookup" \
  --enabled-toolsets "terminal,file,web,search" \
  --deliver "slack:<channel_updates>"
```

See `skills/department-scrum/templates/` for full cron prompt templates with placeholders.

#### Verify

```bash
python3 ~/.hermes/scripts/scrum/test-scrum-cross-dept.py
# Expected: 48/48 tests passing, covering Projects, Products, HR, Finance
```

### 5.3 Extra Department Crons

| Profile | Extra Cron | Schedule |
|---------|-----------|----------|
| hr-manager | Candidate Pipeline | Mon 10AM |
| hr-manager | Recruitment GDrive Sync | Daily 6AM |
| crm-manager | Deal Activity Sync | Hourly 9-18 weekdays |
| crm-manager | Sales Pipeline | Mon 9AM |
| crm-manager | Weekly Summary | Fri 5PM |
| finance-manager | Daily Burn Rate | Daily 8AM |
| finance-manager | Invoice Aging | Mon 8AM |
| finance-manager | Monthly P&L | 1st of month 8AM |
| finance-manager | Weekly Budget | Mon 8AM |
| procurement-manager | Contract Expiry | Mon 9AM |
| product-manager | Sprint Cycle | Bi-weekly Mon |
| hr-manager | Jibble Attendance | Weekdays 9:30AM |
| hr-manager | Jibble Timesheet | Weekly Mon 10AM |

## Phase 6: Model Configuration

### 6.1 Set Up Model Presets

Two named presets:

**Standard** (most profiles):
```yaml
model:
  default: deepseek-v4-flash
  provider: custom:primary-provider
  fallback:
    - provider: backup-provider
      model: deepseek/deepseek-v4-flash
```

**Coding** (coding-agent only):
```yaml
model:
  default: claude-sonnet-4
  provider: anthropic
  fallback:
    - provider: custom:primary-provider
      model: deepseek-v4-flash
```

### 6.2 Switch Profile

```bash
python3 scripts/switch-profile.py <profile-name> --model standard
python3 scripts/switch-profile.py coding-agent --model coding
```

## Phase 7: Verification

### 7.1 Health Check

```bash
# Test gbrain connectivity
hermes -p hr-manager --exec "mcp_gbrain_get_health"

# Test Slack delivery
hermes -p hr-manager --exec "send_message('Standup agent online')"

# Test cron
hermes -p hr-manager cron run <job-id>
```

### 7.2 Verify Each Profile

```bash
# Check all profiles respond
for p in hr-manager finance-manager project-manager procurement-manager \
         product-manager crm-manager marketing-manager compliance-manager \
         customer-support coding-agent; do
  echo "$p: $(hermes -p $p --exec 'mcp_gbrain_whoami' 2>&1 | head -1)"
done
```

## Phase 8: Go Live

When ready to activate, unpause all template cron jobs:

```bash
# List template crons (from profile cron/jobs/*.md)
# Activate each via hermes cron create or un-pause existing
hermes cron list --profile hr-manager
hermes cron resume <job-id>
```

## Post-Setup

- Monitor token utilization weekly (cron already set up)
- Check brain health: `gbrain doctor`
- Review standup summaries for quality
- Extend with new recipes as needs emerge
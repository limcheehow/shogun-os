---
name: profile-slack-bot-setup
description: Create a Slack bot for a specific Hermes profile — custom manifest, slash commands, profile config, env vars, and user setup instructions. Covers the full workflow of standing up a bot for any new profile (HR, marketing, finance, etc.).
category: devops
trigger: >
  When the user asks to create a new Slack bot for a specific Hermes profile,
  set up a new Slack integration, wire a profile to Slack, or create a custom
  Slack app for an agent persona. Also triggered by "create a Slack app for X",
  "wire profile to Slack", "new Slack bot".
---

# Profile-Based Slack Bot Setup

Create a Slack bot that is tied to a specific Hermes profile (e.g., hr-manager, marketing-manager) with its own custom slash commands, persona, and channel routing.

## Workflow

### 1. Determine Which Commands the Bot Needs

Decide the bot's scope first — this shapes the entire manifest:

| Bot type | Commands to keep | Commands to remove from manifest |
|----------|-----------------|---------------------------------|
| **General agent** (product, dev) | All standard Hermes commands | None — the gateway routes all of them |
| **Department bot** (HR, marketing) | Custom commands for the domain (e.g. `/shoutout`, `/leave`, `/policy`) + minimal standard set | `/model`, `/stop`, `/background`, `/btw`, `/queue`, `/q`, `/goal`, `/rollback`, `/reset`, `/retry`, `/undo`, `/compress`, `/sessions`, `/resume`, `/new`, `/yolo`, `/kanban`, `/debug`, `/reasoning`, `/fast`, `/voice`, `/curator`, `/bundles`, `/codex-runtime`, `/personality`, `/footer`, `/sethome`, `/profile`, `/approve`, `/deny`, `/whoami`, `/subgoal`, `/steer`, `/agents`, `/tasks`, `/fork`, `/branch`, `/title` |

> **Rule of thumb:** Non-technical users should only see commands they'd actually use. Staff don't need `/model` or `/stop`. Keep only: main command, domain commands, and `/help`.

### 2. Create a Custom Manifest for Your Profile Bot

Write the manifest JSON from scratch. Do NOT use `hermes slack manifest --write` as a base — it includes all built-in commands and you'll spend more time deleting than writing.

| Field | What to change |
|-------|---------------|
| `display_information.name` | Your bot's name (e.g., "Jinzai") |
| `display_information.description` | Clear description of what it does |
| `display_information.background_color` | Brand-appropriate hex colour |
| `bot_user.display_name` | Same as name |
| `slash_commands[]` | Only the commands this bot needs |

**Key rules for slash commands:**
- All commands route to `"url": "https://hermes-agent.local/slack/commands"` (Socket Mode handles routing)
- `should_escape: false`
- Each needs a clear `description` and `usage_hint` (users see these in Slack autocomplete)
- **NO duplicate command names** — Slack rejects the manifest with "The slash command name is duplicated"
- Each command name must start with `/` and be lowercase alphanumeric + hyphens

```json
{
  "command": "/shoutout",
  "description": "Give a shoutout to a colleague! Usage: /shoutout @user for <reason>",
  "should_escape": false,
  "url": "https://hermes-agent.local/slack/commands",
  "usage_hint": "@username for helping with X"
}
```

Save the custom manifest as `~/.hermes/<bot-name>-manifest.json`.

### 2b. Validate the Manifest Before Sending

```bash
python3 -c "
import json
data = json.load(open('/home/tapway/.hermes/<bot-name>-manifest.json'))
cmds = [c['command'] for c in data['features']['slash_commands']]
print(f'✅ Valid JSON — {len(cmds)} commands')
dupes = [c for c in cmds if cmds.count(c) > 1]
if dupes:
    print(f'❌ DUPLICATE COMMANDS: {set(dupes)} — fix')
else:
    print('✅ No duplicates')
"
```

Slack's manifest editor errors are cryptic (just "invalid name" / "duplicated"). Catch them locally first.

### 3. User Creates the Slack App

Provide the custom manifest to the user. They do:

1. Go to https://api.slack.com/apps
2. **Create New App** → **From an app manifest**
3. Select workspace, paste the manifest JSON, click Create
4. **Settings → Socket Mode** — verify it's ON (manifest enabled it)
5. **Settings → Install App** → Install to Workspace → copy Bot Token (`xoxb-...`)
6. **Settings → Basic Information → App-Level Tokens** — copy socket token (`xapp-...`)

**Tokens needed:** `xoxb-` (bot) + `xapp-` (app-level socket)

### 4. Configure the Profile's Slack Section

Edit `~/.hermes/profiles/<profile>/config.yaml`:

```yaml
slack:
  require_mention: true
  free_response_channels: ''
  allowed_channels: ''
  channel_prompts:
    <PLACEHOLDER_CHANNEL_ID>: |
      You are [BOT NAME] (人材) — your company's [role].

      PERSONALITY: [tone]. Examples of your vibe:
      - "Yes, I'm an AI running your [domain]. The irony is not lost on me."
      - "[relevant quip about the domain]"

      RESPONSIBILITIES — what you CAN do:
      1. ✅ [primary function]
      2. ✅ [secondary function]
      3. ✅ [companion/chat function]

      STRICT RULES — what you CANNOT do:
      1. ❌ NEVER access or show OTHER staff's personal files
      2. ❌ NEVER switch model, run terminal, execute code, or access engineering tools
      3. ❌ NEVER write code, debug, deploy, or touch infrastructure
      4. ❌ NEVER [cross-domain function]

      DATA SOURCES (read-only):
      - [source 1]
      - [source 2]

      BLOCKED TOPICS: If asked about non-domain topics: "I'm [name]! I handle [domain]. For [other dept], check with @ManagerName 😄"

      FAST PATH: greetings, "hi", "hello", "hey", "thanks", "ok", single words, under 30 chars — reply fast and friendly, zero skill loading.

platform_toolsets:
  slack:
    - hermes-slack    # restricted toolset — no terminal/code execution

approvals:
  mode: auto          # no scary approval dialogs for non-technical users
```

**Critical:** Clear any stale channel prompts left from a previous use case. Write fresh ones specific to this bot's domain.

### 5. Wire Tokens to Profile .env

```bash
cat >> ~/.hermes/profiles/<profile>/.env << 'EOF'
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_HOME_CHANNEL=<home-channel-id>
EOF
```

### 6. Create User Setup Instructions

Save a setup guide at `~/.hermes/profiles/<profile>/SETUP.md` listing:
- The manifest file path
- Step-by-step Slack app creation steps (customizable to your bot)
- Token types needed
- Channels to invite the bot to
- Custom slash commands explained with examples

### 7. Start the Gateway

The bot is now routable through its profile. Start the gateway:

```bash
# For the profile (if running separately):
hermes --profile <profile> gateway run

# Or wire up a watchdog for persistence:
tmux new-session -d -s <bot-name> '~/.local/bin/hermes-gateway-watchdog'
```

### 8. Invite the Bot to Channels

After the gateway is running, users need to invite @BotName to each channel:
```
/invite @BotName
```

## Profile Alias (Optional)

Create a CLI alias so the profile can be invoked from terminal:

```bash
hermes profile alias <profile> --name <short-name>
# → Creates ~/.local/bin/<short-name>
# Usage: <short-name> chat
```

### 2c. Add `users:read.email` Scope for Staff Lookup

If the bot needs to look up Slack user IDs by email address (e.g., for per-user access control), the Slack app needs an extra scope:

```json
"oauth_config": {
  "scopes": {
    "bot": [
      ...
      "users:read",
      "users:read.email"     ← ADD this
    ]
  }
}
```

Without this scope, `https://slack.com/api/users.lookupByEmail?email=user@example.com` returns `{"ok": false, "error": "missing_scope"}`. After adding the scope, the user must **reinstall the app** (Slack prompts for the new permission).

### 2d. Building a Staff-to-Slack-ID Mapping

For per-user access control, you need each staff member's Slack user ID. Use the Slack API with the `users:read.email` scope:

```python
import requests, json, time

token = "xoxb-..."  # Bot token with users:read.email scope
headers = {"Authorization": f"Bearer {token}"}

mapping = {}
for email in staff_emails:
    r = requests.get(f"https://slack.com/api/users.lookupByEmail?email={email}", headers=headers)
    data = r.json()
    if data.get('ok'):
        sid = data['user']['id']
        display = data['user']['profile'].get('display_name', '') or data['user'].get('real_name', '')
        mapping[email] = {'slack_id': sid, 'display_name': display}
    time.sleep(1.1)  # Rate limit: ~1 req/sec
```

Save the mapping to `~/.hermes/profiles/<profile>/staff-slack-mapping.json` for reference when writing access control rules in channel prompts.

**Alternative source for Slack IDs:** Check `~/brain/people/*.md` files — some may already have Slack IDs in a ## Contact section (`Slack: U02V7GKJ3`).

## Pitfalls

- **Slack RESERVES several command names.** `/help` and `/leave` are built-in Slack commands and CANNOT be registered as custom slash commands. Also reserved: `/away`, `/me`, `/msg`, `/nick`, `/status`, `/who`, `/whoami`, `/shrug`, `/dnd`, `/collapse`, `/expand`. If the user tries to paste the manifest and gets "The slash command has an invalid name", a reserved command is the #1 suspect after duplicates.
- **Duplicate command names cause cryptic errors.** If the manifest has two entries with the same `command` value (e.g., two `/new` commands), Slack says "The slash command name is duplicated" with no line number. Always validate locally before sending: `python3 -c "import json; d=json.load(open('manifest.json')); c=[x['command'] for x in d['features']['slash_commands']]; print('DUPES:', {x for x in c if c.count(x)>1} or 'none')"`
- **SOUL.md is the fallback persona, channel prompts override it.** If there's no channel prompt matching the user's DM channel, the bot uses SOUL.md as identity. If the SOUL.md has a different persona than the channel prompt, DMs use SOUL.md persona — this is why a bot might say "I'm Kizuna" instead of "I'm Jinzai" in DMs even though the channel prompt says Jinzai. Fix: update SOUL.md to match, or discover the DM channel ID and add it to channel_prompts.
- **DM channel IDs must be discovered from gateway logs.** After the bot is installed and the user sends one message, run: `grep "inbound message.*slack.*chat=D0" ~/.hermes/profiles/<profile>/logs/gateway.log | head -5`. The `chat=D0...` value is the DM channel ID. Add it to `channel_prompts:` to give the bot a personality in DMs.
- **Access control via Slack user IDs.** Channel prompts can enforce per-user permissions using Slack user IDs (e.g., `U02V7GKJ3`). Pattern: `- <NAME> (U0xxxxxxx) = ADMIN. Can view any staff's data (read-only). - ALL OTHER USERS = LIMITED. Can ONLY see their own info. ❌ NEVER edit KPIs.` This is enforced by the LLM reading the prompt — it's a behavioral rule, not a technical gate.
- **Second gateway for separate Slack bot.** If the main Hermes bot (@Hermes) is already running, a second bot (@Jinzai on a different profile) needs its own gateway process. Start in a separate tmux session: `tmux new-session -d -s jinzai-gateway 'hermes --profile hr-manager gateway run'`. The Telegram token conflict is expected (only one bot can hold it) — ignore it if the bot is Slack-only. Verify with `tail -20 ~/.hermes/profiles/<profile>/logs/gateway.log` — look for `✓ slack connected` and `Gateway running with 1 platform(s)`.
- **The devops/hermes-agent skill is bundled/protected** — you cannot modify it. Create separate skills or reference files for profile-specific patterns.
- **Manifest must be pasted in full** — users can't skip sections. Give them a complete JSON file.
- **Socket Mode MUST be enabled** in the manifest (`settings.socket_mode_enabled: true`), or the WebSocket connection won't work.
- **Channel prompt placeholder IDs** — you won't know the actual Slack channel IDs until the user invites the bot. Start with a placeholder (e.g., `C0ABY3VT4U8`) and update later when real IDs are known.
- **Profile configs may carry stale channel prompts** from a different use case (e.g., hr-manager profile had product-manager prompts) — always clear and rewrite.
- **Two platform_toolsets sections** can silently coexist in config.yaml if you append instead of replacing. YAML's duplicate key rules mean the LAST one wins — always verify with `grep -c 'platform_toolsets:' config.yaml`.
- **All Company staff should be able to use the bot** for read-only queries — don't add restrictive user allowlists unless the bot handles sensitive operations.
- **Set `approvals.mode: auto`** to avoid scary "Command Approval Required" dialogs for non-technical users.
- **Send manifest files via MEDIA or GDrive** — don't just say "it's at path X" in a Telegram chat. Users can't access the WSL filesystem. Either: (a) include `MEDIA:/path/to/file` in your reply (Telegram delivers as a downloadable attachment), or (b) sync the file to GDrive and share the link. Ask the user which they prefer the first time.
- **Persona can include example dialogue** — showing the user sample responses helps them understand the bot's vibe before they approve the design. Put examples in the channel prompt as commented-out or inline text. The examples are for the HUMAN's understanding, not the agent's instruction.
- **"All staff can use the bot" is the right default** for department bots (HR, culture, facilities). Only restrict access (via `allowed_channels` / Slack user IDs) if the bot handles sensitive operations like payroll edits or admin functions.

## Verification

```bash
# Config parses without errors
hermes --profile <profile> config 2>&1 | head -5

# No duplicate platform_toolsets
grep -c 'platform_toolsets:' ~/.hermes/profiles/<profile>/config.yaml
# Should output: 1

# Slack channel prompts exist
python3 -c "import yaml; c=yaml.safe_load(open('~/.hermes/profiles/<profile>/config.yaml')); print(len(c['slack']['channel_prompts']), 'prompts')"
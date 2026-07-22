---
name: company-profile-routing
description: Route Company Hermes profiles to Telegram groups — chat ID discovery, multi-bot architecture, channel_prompts editing, and gateway restart verification. Use when a profile shows "not yet routed" or the user asks to assign a profile to a Telegram group.
---

# Company Profile → Telegram Routing

Route any Company your-product profile (Kata, Kizuna, Kura, Koku, etc.) to a Telegram group so it responds with its persona in that group.

## Profile Roster & Telegram Bots

Company profiles use one of two Telegram bots. Know which profile uses which bot before routing — if the wrong bot isn't in the group, messages silently fail.

| Profile | your-product Name | Bot | Bot Username | Status |
|---|---|---|---|---|
| `default` | Hermes | Main Hermes bot | (main) | All channels |
| `product-manager` | — | Main Hermes bot | (main) | Routed: `-1003882643127` (Company Product) |
| `marketing-manager` | Haiku | Main Hermes bot | (main) | Routed: `-1003958841816` (Company Marketing) |
| `compliance-manager` | Kata | Main Hermes bot | (main) | Routed: `-5205962952` (Company Management) |
| `hr-manager` | Kizuna | — | — | Not yet routed |
| `procurement-manager` | Kura | — | — | Not yet routed |
| `finance-manager` | Koku | — | — | Not yet routed |

**When a profile uses the main Hermes bot**, add a `channel_prompts` entry to the main gateway's config.yaml (~/.hermes/config.yaml) and the main gateway handles routing. No separate gateway needed. All current Company profiles use this pattern.

## Routing Workflow

### 1. Determine the bot

Check `~/.hermes/profiles/<name>/.env` for `TELEGRAM_BOT_TOKEN`. If it matches the main bot token, it's main-bot-routed. If it's different, it's separate-bot-routed.

```bash
grep 'TELEGRAM_BOT_TOKEN=*** ~/.hermes/.env | head -1
grep 'TELEGRAM_BOT_TOKEN=*** ~/.hermes/profiles/<name>/.env | head -1
```

### 2. Find the Telegram group's chat ID

**Primary method — gateway logs** (works even if the bot hasn't joined the group yet):

```bash
# List all group chat IDs the main bot knows about
grep -oP 'chat=-?\d+' ~/.hermes/logs/gateway.log | sort -u | grep '^-'
# Groups are negative numbers (e.g., -1003882643127, -5205962952)
```

To identify WHICH group each ID maps to, grep for the first message from each:

```bash
grep 'chat=-1003882643127' ~/.hermes/logs/gateway.log | grep 'msg=' | head -1
```

**Fallback — Telegram API** (only works if the bot is already in the group). Use the `send_message(action='list')` tool to see available targets, or call `getUpdates` with the bot's token:

```bash
python3 /dev/stdin << 'SCRIPT'
import json, urllib.request, re

with open('/home/tapway/.hermes/.env') as f:
    text = f.read()
m = re.search(r'TELEGRAM_BOT_TOKEN=*** text.split('\n'):
    if 'TELEGRAM_BOT_TOKEN=*** in line:
        token = line.split('=', 1)[1].strip()
        break

resp = urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getUpdates')
data = json.loads(resp.read())
for u in data.get('result', []):
    chat = u.get('message', {}).get('chat', {}) or u.get('my_chat_member', {}).get('chat', {})
    if chat.get('title'):
        print(f'{chat["id"]} -> {chat["title"]}')
SCRIPT
```

### 3. Edit the profile's config.yaml

Add a `channel_prompts` entry under `telegram:` for the group chat ID. **Use Python insertion, not patch()** — patch() frequently fails on multi-line YAML channel prompt strings due to whitespace matching issues.

```bash
python3 << 'PYEOF'
with open('/home/tapway/.hermes/profiles/<name>/config.yaml', 'r') as f:
    lines = f.readlines()

# Insert new channel prompt before "allowed_chats" line
new_entry = """    '-<CHAT_ID>': "You are <PERSONA>...\\\n      \\ ...\\\n      \\ ...\\n"\n"""

for i, line in enumerate(lines):
    if line.rstrip() == "  allowed_chats: ''" and i > 400:
        insert_idx = i
        break

lines.insert(insert_idx, new_entry)

with open('/home/tapway/.hermes/profiles/<name>/config.yaml', 'w') as f:
    f.writelines(lines)
PYEOF
```

**Channel prompt template** — adapt from the profile's SOUL.md:

```yaml
telegram:
  channel_prompts:
    '-<CHAT_ID>': "You are <your-product NAME> — your company's <ROLE>.\\
      \\ PERSONALITY: <from SOUL.md>.\\
      \\ ALWAYS LOAD: <skills from SOUL.md>.\\
      \\ TOOLS: <allowed tools>.\\
      \\ BLOCKED: <blocked tools>.\\
      \\ KEY PATHS: <paths from SOUL.md>.\\
      \\ RESPONSE STYLE: <from SOUL.md>.\\n"
```

### 4. Verify the config

```bash
hermes config --profile <name> 2>&1 | head -5
```

Should show the config banner with NO `⚠️ Failed to parse` warning. If you see a parse warning, the YAML is broken — fix before restarting any gateway.

### 5. Add bot to the Telegram group

- **Main-bot-routed**: Skip — main bot is already in the group
- **Separate-bot-routed**: Invite the bot (e.g., `@gozen_sam_bot`) to the group manually via Telegram

### 6. Start/restart the gateway

- **Main-bot-routed**: Restart the main gateway for channel_prompts changes to take effect. **Ask the user before restarting.**
- **Separate-bot-routed**: Start a separate gateway for the profile:
  ```bash
  tmux new-session -d -s <name>-gateway "~/.local/bin/<your-product-name> gateway run"
  ```
  The `<your-product-name>` CLI wrapper auto-sets `--profile <name>`.

## Tele group Authorization: `TELEGRAM_GROUP_ALLOWED_CHATS` (env var)

Instead of per-user `TELEGRAM_ALLOWED_USERS`, use `TELEGRAM_GROUP_ALLOWED_CHATS` in `~/.hermes/.env` to authorize **all members** of listed groups at once. No manual user management needed — anyone in these groups can interact with the bot.

```
TELEGRAM_GROUP_ALLOWED_CHATS=-1003773708968,-1003882643127,-1003958841816,-5205962952
```

This is SET in your company's `.env`. Gateway restart required after change. Use this for HR groups where members change frequently.

## Pitfalls

- **Different bots, different tokens**: If a profile has its own `TELEGRAM_BOT_TOKEN` in `~/.hermes/profiles/<name>/.env`, adding channel_prompts to the main gateway won't route to that bot. The profile needs its own gateway process. Currently all Company profiles use the main Hermes bot — no separate gateways needed.
- **getUpdates returns empty**: Happens when the bot hasn't been added to the group yet. Use gateway logs instead — search for `chat=-` group IDs the main bot already knows.
- **patch() fails on channel_prompts**: The YAML continuation strings (`\\` at line ends) make exact string matching unreliable. Use Python file insertion instead.
- **Telegram privacy mode**: Bots in groups can only read messages mentioning them or replying to them unless made admin or privacy mode is disabled via @BotFather.
- **Never restart without asking**: Gateway restart kills active agent conversations. Always get explicit user permission.
- **Config parse errors are silent**: The gateway falls back to defaults on parse failure. Always run `hermes config --profile <name>` after editing to verify.
- **Context-window thrashing on long sessions**: Multi-turn routing tasks (e.g., "Route Kata to this group") can degrade into 48+ API calls and 8-minute responses as context grows and the model loses earlier instructions. If the agent starts looping or asking repeated clarifying questions, use /new to reset the session and give the routing command fresh.

# Slack Platform Channel Configuration

## Channel Prompts Must Be a YAML Dict

`channel_prompts` in the Slack platform config MUST be a YAML **dict** (key-value pairs), NOT a string.

### ❌ BROKEN — String format

This silently fails. The gateway code does `config_extra.get("channel_prompts") or {}` then checks `isinstance(prompts, dict)`. A string returns `None` — the prompt is never applied.

```yaml
slack:
  channel_prompts: "D0B0LU0HP4L:FAST PATH (check first): greetings..."
```

### ✅ CORRECT — Dict format

```yaml
slack:
  channel_prompts:
    D0B0LU0HP4L: "PRODUCT MANAGER ONLY..."
    C0308PA6Y: "SCRUM CHANNEL..."
    C0ABY3VT4U8: "SPRINT MANAGEMENT..."
```

### How It Works

`resolve_channel_prompt()` in `gateway/platforms/base.py` (line 1180):
1. Reads `config_extra.get("channel_prompts")` — must be a dict
2. Looks up `channel_id` first, then `parent_id` (for threads)
3. Returns the prompt string or None
4. Returns `None` immediately for non-dict values

## allowed_channels — CRITICAL: DMs Are Never Filtered

`allowed_channels` controls which **public/private channels** the bot responds in. **DMs are ALWAYS allowed regardless of this setting.**

This is in the gateway code at `slack.py` line 3017:
```python
"""DMs are never filtered."""
```

### What this means:
- `allowed_channels: D0B0LU0HP4L, C0308PA6Y, C0ABY3VT4U8` — bot responds in those 3 channels AND any DM
- `allowed_channels: ''` (empty) — bot responds everywhere it's mentioned

### Strategy for restrictive setups:
Since DMs are always open (for scrum replies, etc.), prefer leaving `allowed_channels: ''` and relying on:
1. `require_mention: true` — bot only responds when @mentioned in public channels
2. Channel prompts with hard scope rules for the 3 managed channels
3. Skill-level access control by Slack user ID

This avoids blocking team members who need to reply via DM (scrum, ad-hoc questions).

### `free_response_channels`

Channels where the bot responds WITHOUT being @mentioned:
```yaml
slack:
  free_response_channels: D0B0LU0HP4L
```
Only Admin's DM — everyone else must @mention the bot.

## Per-Channel Prompt Strategy

Each channel prompt is context-specific. Write prompts that:

1. **Declare scope first** — e.g. "PRODUCT MANAGER ONLY" or "SCRUM CHANNEL"
2. **List allowed skills** — which skills the agent may load in this channel
3. **Block dangerous skills** — notion, linear, creative, web_search, session_search, terminal execution
4. **Provide a refusal script** — what to say when asked out-of-scope questions
5. **Specify data source** — where to read/write data

### ACCESS CONTROL by Slack User ID

Channel prompts can embed per-user access rules by referencing Slack user IDs:

```yaml
channel_prompts:
    D0B0LU0HP4L: "ACCESS CONTROL — USER ID U02V7GKJ3 = Admin (full access).
        USER ID U0A9DCBCJSH = Jason (full access).
        ALL OTHER USERS: READ ONLY on PRDs. NO edit/delete epics without approval.
        NO roadmap or stakeholder changes."
    C0308PA6Y: "ACCESS CONTROL — Any user can view. Only Admin (U02V7GKJ3)
        and Jason (U0A9DCBCJSH) can modify."
```

Combine with skill-level rules (in `tapway-product-agent` SKILL.md) that tell the agent to check the message sender's Slack user ID before performing any write/delete operation.

### Per-channel prompt patterns (Company):

**Admin DM (D0B0LU0HP4L):**
```
PRODUCT MANAGER ONLY. ALLOWED: company-product-agent, product-manager, 
tapway-roadmap, company-metrics, company-stakeholder-updates, 
tapway-competitive-intel, brainstorming. 
BLOCKED: notion, linear, github-issues, airtable, creative, web_search, 
session_search, terminal, execute_code.
ACCESS CONTROL — U02V7GKJ3 = Admin (full). U0A9DCBCJSH = Jason (full).
Others: READ ONLY on PRDs, no roadmap edits, epic delete needs approval.
```

**Scrum channel (C0308PA6Y):**
```
SCRUM ONLY. ALLOWED: company-product-agent, product-manager.
BLOCKED: everything else.
ACCESS CONTROL — U02V7GKJ3 and U0A9DCBCJSH can modify sprint data.
Others: view scrum status only.
```

**Sprint channel (C0ABY3VT4U8):**
```
SPRINT MANAGEMENT ONLY. ALLOWED: company-product-agent, product-manager,
tapway-roadmap, company-stakeholder-updates.
BLOCKED: everything else.
ACCESS CONTROL — U02V7GKJ3 and U0A9DCBCJSH have full access.
Others: read-only sprint data.
```

## Gateway Restart Required

Config changes to `channel_prompts`, `allowed_channels`, or any `slack:` section take effect **only after gateway restart**. The old config stays in memory until the gateway re-reads `config.yaml`.

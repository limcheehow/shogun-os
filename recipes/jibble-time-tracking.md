---
id: jibble-time-tracking
name: Jibble Time Tracking
version: 2.0.0
description: >
  ⚠ SUPERSEDED by Provider Abstraction. See recipes/time-tracking/ instead.
  Jibble is now a reference bridge at recipes/time-tracking/bridges/tt-bridge-jibble.py.
  The generic time tracking skill at recipes/time-tracking/GENERIC_SKILL.md works
  with any provider that implements the CONTRACT.md standard tools.
category: connector
requires: []
secrets: []
health_checks: []
setup_time: 5 min
cost_estimate: "$0 (included with Jibble subscription)"
---

# Jibble Time Tracking

> **⚠ DEPRECATED — This recipe is superseded by the [Provider Abstraction](../time-tracking/CONTRACT.md).**

Instead of a Jibble-specific recipe, use the new **generic** approach:

1. Read [`CONTRACT.md`](../time-tracking/CONTRACT.md) — standard tool interface
2. Configure the Jibble bridge as MCP server (see below)  
3. Read [`GENERIC_SKILL.md`](../time-tracking/GENERIC_SKILL.md) — works with any provider

## Quick Migration

Configure Jibble via the new bridge:

```yaml
mcp_servers:
  time-tracking:
    command: python3
    args: [~/.hermes/scripts/tt-bridge-jibble.py]
    env:
      TT_API_KEY: "${TT_API_KEY}"
```

```bash
# Symlink the reference bridge into ~/.hermes/scripts/
ln -sf ~/company-os/recipes/time-tracking/bridges/tt-bridge-jibble.py ~/.hermes/scripts/tt-bridge-jibble.py
```

> See [`bridges/tt-bridge-jibble.py`](../time-tracking/bridges/tt-bridge-jibble.py) for the reference implementation.

## IMPORTANT: Instructions for the Agent

**You are the installer.** This recipe combines three layers:

1. **MCP server config** — adds Jibble queries as tools available to the agent
2. **Hermes skill** — reusable agent-facing workflows for time queries and timesheet ops
3. **Cron templates** — automated daily/weekly summaries for HR oversight

## Architecture

```
Jibble API
  ↓ API Key
MCP Server (configured in ~/.hermes/config.yaml)
  ↓ Tools available to agent:
  ├── jibble_get_entries       (time entries by date/user)
  ├── jibble_get_members       (active members list)
  └── jibble_get_projects      (project time tracking)
  ↓
Hermes skill (SKILL.md)
  ↓ Agent workflows:
  ├── "Who's clocked in today?"
  ├── "Show yesterday's timesheet"
  └── "Weekly attendance summary"
  ↓
Cron jobs (hr-manager profile)
  ├── Daily 9AM: check late arrivals
  └── Weekly Monday: compile timesheet digest
```

## Prerequisites

1. Jibble account with admin/manager access
2. Jibble API key (from Integrations → API Keys in Jibble dashboard)
3. `~/.hermes/config.yaml` writable (for MCP server config)

## Setup Flow

### Step 1: Configure Jibble MCP Server

Add to `~/.hermes/config.yaml` or the profile-level config (this is profile-specific — **hr-manager**):

```yaml
mcp_servers:
  jibble:
    type: url
    url: https://api.jibble.io/v1/mcp
    headers:
      X-Api-Key: "${JIBBLE_API_KEY}"
    # OR use stdio transport if there's a local MCP bridge
```

If Jibble doesn't expose a native MCP endpoint, create a thin HTTP-to-MCP bridge in `~/.hermes/scripts/jibble-mcp-bridge.py`:

```python
#!/usr/bin/env python3
"""Jibble MCP bridge — wraps Jibble REST API as stdio MCP tools."""
import json, sys, os, urllib.request

API_KEY = os.environ.get("JIBBLE_API_KEY", "")
BASE_URL = "https://api.jibble.io/v1"

def handle_request(req):
    method = req.get("method")
    params = req.get("params", {})

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "jibble_get_entries",
                    "description": "Get time entries for a date range",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string", "description": "Start date YYYY-MM-DD"},
                            "to": {"type": "string", "description": "End date YYYY-MM-DD"},
                            "memberId": {"type": "string", "description": "Optional member filter"}
                        }
                    }
                },
                {
                    "name": "jibble_get_members",
                    "description": "Get active team members",
                    "inputSchema": {"type": "object", "properties": {}}
                },
            ]
        }

    elif method == "tools/call":
        tool = params.get("name")
        args = params.get("arguments", {})
        headers = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}

        if tool == "jibble_get_entries":
            url = f"{BASE_URL}/entries?from={args['from']}&to={args['to']}"
            if args.get("memberId"):
                url += f"&memberId={args['memberId']}"
            req = urllib.request.Request(url, headers=headers)

        elif tool == "jibble_get_members":
            req = urllib.request.Request(f"{BASE_URL}/members", headers=headers)

        else:
            return {"error": f"Unknown tool: {tool}"}

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
            return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}]}
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Unknown method: {method}"}

# STDIO MCP protocol
for line in sys.stdin:
    try:
        request = json.loads(line.strip())
        response = handle_request(request)
        response["id"] = request.get("id")
        print(json.dumps(response), flush=True)
    except json.JSONDecodeError:
        continue
```

### Step 2: Store the API Key

```bash
# Add to ~/.hermes/.env (read by Hermes at startup)
echo 'JIBBLE_API_KEY="your-api-key-here"' >> ~/.hermes/.env

# Or for profile-specific, add to profile config:
echo 'JIBBLE_API_KEY: "your-api-key-here"' >> ~/.hermes/profiles/hr-manager/config.yaml
```

### Step 3: Create the Hermes Skill

Write to `~/tapway-hermes/recipes/references/jibble-skill.md` as a draft (or directly to `~/.hermes/profiles/hr-manager/skills/jibble-time-tracking/SKILL.md` once active):

The skill should support:
- **"Who's clocked in today?"** → Query `jibble_get_entries` for today, filter active entries, map member names
- **"Show yesterday's timesheet for {name}"** → Query with member filter, format as table
- **"Weekly attendance summary"** → Aggregate entries by member, flag missing days
- **"Detect late arrivals"** → Compare first entry time against 9AM threshold

### Step 4: Create Cron Templates

In the **hr-manager** profile:

**Daily attendance check** (weekdays 9:30AM):
```bash
hermes cron create \
  --name "Jibble Daily Attendance" \
  --schedule "30 9 * * 1-5" \
  --prompt "$(cat <<'PROMPT'
## Jibble Daily Attendance Check

Check who's clocked in today using the Jibble MCP tool jibble_get_entries.
List:
1. Who is clocked in (currently active)
2. Who is late (scheduled to start by 9AM, no entries)
3. Who is absent (no entry at all today)

Flag anyone who hasn't clocked in by 9:30AM.
Deliver a brief report to the HR channel.
PROMPT
)" \
  --skills "jibble-time-tracking" \
  --enabled-toolsets "terminal" \
  --deliver origin
```

**Weekly timesheet roundup** (Monday 10AM):
```bash
hermes cron create \
  --name "Jibble Weekly Timesheet" \
  --schedule "0 10 * * 1" \
  --prompt "$(cat <<'PROMPT'
## Jibble Weekly Timesheet Roundup

Query Jibble for last week's time entries (Mon-Sun).
Compile a summary:
1. Total hours per team member
2. Any missing days or anomalies
3. Overtime flagged
4. Compare against expected weekly hours

Deliver to the HR channel as a formatted table.
PROMPT
)" \
  --skills "jibble-time-tracking" \
  --enabled-toolsets "terminal" \
  --deliver origin
```

### Step 5: Verify

```bash
# Test the MCP bridge
echo '{"id":1,"method":"tools/list"}' | python3 ~/.hermes/scripts/jibble-mcp-bridge.py

# Expected: JSON response listing jibble_get_entries and jibble_get_members
```

## Cost

$0 — included with Jibble subscription. API access is part of the plan.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| MCP bridge returns empty | Check API key. Jibble API may need different base URL or auth format. |
| No entries returned | Check date format (YYYY-MM-DD). Jibble may filter by organization. |
| Cron fails with "tool not found" | MCP server not connected. Check config.yaml mcp_servers section. |
| Bridge crashes on start | Missing Python packages (json, urllib are stdlib — shouldn't fail). |
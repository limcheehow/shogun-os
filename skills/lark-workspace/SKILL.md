---
name: lark-workspace
version: 1.0.0
description: |
  Lark (Feishu) workspace integration — mirror of google-workspace for
  calendar, docs, wiki, drive, tasks, and search. Uses YSzEthan/lark-office-mcp
  for docs/wiki/tasks/search and a native calendar script for events.
triggers:
  - "lark calendar"
  - "feishu"
  - "飞书"
  - "lark workspace"
---

# Lark Workspace

> **Full Lark (Feishu) integration for Hermes Agent.** Mirrors the google-workspace skill using Lark's MCP server for docs/wiki/tasks + a Python calendar wrapper. Designed for Benkei (executive-assistant) profile.

## Architecture

```
Benkei Profile
    ├── MCP: lark-office-mcp (bun)
    │     ├── doc_*       — Read/write/create Lark documents
    │     ├── wiki_*      — Wiki spaces, nodes, pages
    │     ├── drive_*     — Cloud storage listing
    │     ├── todo_*      — Tasks & to-dos
    │     ├── tasklist_*  — Task lists & grouping
    │     ├── subtask_*   — Subtask management
    │     ├── user_*      — User info & directory
    │     ├── section_*   — Task sections/groups
    │     └── lark_search — Global document search
    │
    └── Script: lark_calendar.py (Python)
          ├── list        — List upcoming events
          ├── create      — Create calendar event
          ├── get         — Get event details
          └── delete      — Delete event
```

## Google Workspace ↔ Lark Mapping

| Google Workspace | Lark Equivalent | How |
|-----------------|----------------|-----|
| Calendar API | **lark_calendar.py** | Python script using tenant token |
| Docs API | **doc_*** MCP tools | lark-office-mcp: read, write, create, delete |
| Drive API | **drive_*** MCP tools | lark-office-mcp: list, recent files |
| Task/Reminders | **todo_*** + **tasklist_*** MCP tools | lark-office-mcp: full task management |
| Search | **lark_search** MCP tool | Global doc search |
| Wiki | **wiki_*** MCP tools | lark-office-mcp: read/write wiki pages |
| Gmail | Lark Mail API | (planned — future release) |

## Prerequisites

1. **Lark/Feishu tenant** with admin access
2. **Lark App** created at https://open.feishu.cn/app
3. **bun** installed (`which bun`)
4. lark-office-mcp cloned and installed (`bun install`)

## Setup

### Step 1: Create a Lark App

1. Go to https://open.feishu.cn/app → Create Custom App
2. Note the **App ID** and **App Secret**
3. Add these permissions (API scopes) in the app's Permissions tab:
   - `auth:user:id:read` — identify users
   - `calendar:calendar:readonly` — read calendars
   - `calendar:calendar_event:readwrite` — create/manage events
   - `docx:document:readonly` — read documents
   - `docx:document:readwrite` — write/create documents
   - `drive:drive:readonly` — list files
   - `task:task:readwrite` — manage tasks
   - `wiki:wiki:readonly` — read wiki
4. (Optional) Set app visibility to "All members" if needed

### Step 2: Publish the App

In the Lark Open Platform console:
1. Go to **Security** → Set redirect URL: `http://localhost:9876/callback`
2. Go to **Version Management & Publishing** → Create Version → Apply for permissions → Submit for approval
3. Wait for admin approval

### Step 3: Configure Profile

```bash
# Clone the MCP server into the profile
mkdir -p ~/.hermes/profiles/executive-assistant/mcp-servers
cd ~/.hermes/profiles/executive-assistant/mcp-servers
git clone https://github.com/YSzEthan/lark-office-mcp.git
cd lark-office-mcp && bun install
```

Add to profile config.yaml:
```yaml
mcp_servers:
  lark:
    command: bun
    args: [run, /path/to/lark-office-mcp/src/index.ts]
    env:
      LARK_APP_ID: ${LARK_APP_ID}
      LARK_APP_SECRET: ${LARK_APP_SECRET}
      LARK_CALLBACK_PORT: "9876"
```

### Step 4: Set Environment Variables

```bash
# In the profile's .env file
echo "LARK_APP_ID=cli_xxxxxxxxxxxxx" >> ~/.hermes/profiles/executive-assistant/.env
echo "LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxx" >> ~/.hermes/profiles/executive-assistant/.env
```

### Step 5: Verify

```bash
# Test the MCP server starts
bun run ~/.hermes/profiles/executive-assistant/mcp-servers/lark-office-mcp/src/index.ts

# Test calendar access
LARK_APP_ID=xxx LARK_APP_SECRET=xxx \
  python3 ~/.hermes/profiles/executive-assistant/scripts/lark_calendar.py list
```

## Usage — For the Agent (Benkei)

### Calendar Operations

```
List events tomorrow:
  python3 lark_calendar.py list --start 2026-06-27T00:00:00+08:00 --end 2026-06-27T23:59:59+08:00

Create a meeting:
  python3 lark_calendar.py create --summary "Client Meeting" --desc "With Acme Corp" --start 1700000000 --end 1700003600

Get event:
  python3 lark_calendar.py get --event-id xxxxxx_xxx@xxx

Delete event:
  python3 lark_calendar.py delete --event-id xxxxxx_xxx@xxx
```

### Document Operations (MCP Tools)

Use lark-office-mcp tools via MCP. Key tools for Benkei:

| Task | MCP Tool | Example |
|------|----------|---------|
| Create doc | `doc_create` | Create meeting notes doc |
| Read doc | `doc_read` + `blocks_to_markdown` | Read and summarize |
| Search docs | `lark_search` | Find documents by keyword |
| Manage tasks | `todo_create`, `todo_list` | Set follow-up tasks |
| Wiki | `wiki_read`, `wiki_create_node` | Create internal Wiki pages |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `bun: command not found` | Install bun: `curl -fsSL https://bun.sh/install | bash` |
| MCP server won't start | Check LARK_APP_ID and LARK_APP_SECRET are set in .env |
| `token expired` | OAuth token expires. The MCP server auto-refreshes via OAuth callback |
| `calendar: permission denied` | Add calendar permissions to the Lark app and re-publish |
| MCP tools not showing up | Restart the Hermes session after adding MCP to config |
| Auth popup on first use | The MCP server opens a browser for Lark OAuth on first call — this is expected |
| `tenant_access_token` fails | Verify app is published and permissions are approved |

## Cost

- **Lark/Feishu**: Free tier includes calendar, docs, drive (limits vary by plan)
- **lark-office-mcp**: Open source (MIT) — free
- **Calendar script**: Zero-cost — runs locally

## References

- [Lark Open Platform Docs](https://open.feishu.cn/document/server-docs/docs)
- [lark-office-mcp GitHub](https://github.com/YSzEthan/lark-office-mcp)
- [Lark Calendar API](https://open.feishu.cn/document/server-docs/calendar-v4/calendar-event/introduction)
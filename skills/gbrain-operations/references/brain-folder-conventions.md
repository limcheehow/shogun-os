# Brain Folder Conventions

Semantic folder map for `~/brain/` — what goes where, and how cron jobs should target each.

## Folder Map

| Folder | Purpose | Content Examples | From Cron |
|--------|---------|-----------------|-----------|
| `daily/` | Day-level summaries, briefings, task snapshots | `daily/2026-05-24.md`, `daily/briefings/2026/05/`, `daily/tasks/` | Morning Briefing, End of Day, Task Reminder |
| `daily/briefings/YYYY/MM/` | Morning news digest archive | `2026-05-24.md` with frontmatter `type: morning-briefing` | Morning Briefing 7AM |
| `daily/tasks/` | Daily task state snapshots | `tasks-2026-05-24.md` (verbatim copy of ops/tasks.md) | Task Reminder 7AM |
| `daily/calendar/` | Calendar sync data | `.raw/` JSONs from Google Calendar | Calendar Sync 8AM |
| `ideas/` | Product & business ideas | `ideas/teh-tarik-whatsapp-bot.md` | Email capture, conversation |
| `concepts/` | World concepts coined by others | `concepts/pareto-principle.md`, `concepts/second-brain.md` | Brainstorm/LSD, reading |
| `wiki/` | Evergreen knowledge base | `wiki/tapway-ai-stack.md`, `wiki/personal/reflections/` | Dream cycle synthesis |
| `inbox/` | Capture bucket for unprocessed notes | New content via `gbrain capture` or direct write | gbrain capture, ad-hoc |
| `agent/` | Hermes agent profile definitions | `crm-SOUL.md`, `work-agent-config.yaml` | Manual migration from ~/.hermes/profiles/ |
| `attachments/` | Uploaded images and files | Images and files the user sends to chat | All Telegram sessions |
| `meetings/` | Meeting notes with full transcripts | `2026-05-21-nrf-closed-door-networking.md` | Meeting sync cron |
| `persons/` | Individual person files (6K+) | `persons/thomas-cheah.md` | Email enrichment, calendar enrichment |
| `companies/` | Company files (5K+) | `companies/tapway.md` | Email enrichment, deal tracking |
| `deals/` | Sales deal pipeline pages | `deals/appomax-mou.md` | Sales enquiry pipeline |
| `ops/` | Operational files | `ops/tasks.md` (task list), `ops/` | Task reminder |

## Authorship Test

When routing content to the correct folder:

| Signal | Destination |
|--------|-------------|
| User generated the idea | `originals/` (or `wiki/personal/reflections/`) |
| User's unique synthesis of others' ideas | `originals/` (the synthesis is original) |
| World concept someone else coined | `concepts/` |
| Product or business idea | `ideas/` |
| User's ghostwritten book/essay | `originals/` (note ghostwriter in metadata) |
| Article ABOUT user | `media/writings/` |

## Cron-to-Brain Writing Convention

Every daily cron should write a persistent brain page in addition to its Slack delivery.

### Pattern

```
### Step N: Save to Brain
Create a permanent page with date-based filename and frontmatter:
```

| Cron Type | Destination | Frontmatter Tags |
|-----------|-------------|------------------|
| Morning briefing / news digest | `daily/briefings/YYYY/MM/YYYY-MM-DD.md` | `[daily, briefing, news]` |
| Task state snapshot | `daily/tasks/tasks-YYYY-MM-DD.md` | none (verbatim copy) |
| End-of-day summary | `daily/YYYY-MM-DD.md` | `[daily, log]` |
| Weekly/periodic reports | `daily/reports/YYYY-MM-DD-{type}.md` | `[daily, report, {type}]` |
| Entity enrichment (email/crm) | Timelines on existing `persons/`, `companies/`, `deals/` files | append timeline entries |

### Implementation

```bash
YEAR=$(date +%Y)
MONTH=$(date +%m)
mkdir -p ~/brain/daily/briefings/$YEAR/$MONTH
cat > ~/brain/daily/briefings/$YEAR/$MONTH/$YEAR-$MONTH-$DAY.md << 'EOF'
---
type: morning-briefing
date: YYYY-MM-DD
tags: [daily, briefing, news]
---

[content]
EOF
```

The next dream cycle sync picks these up automatically. No gbrain command needed — just write the file.
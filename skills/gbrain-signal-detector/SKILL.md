---
name: gbrain-signal-detector
description: "Always-on ambient signal capture for gbrain. Detects original thinking, entity mentions, and ideas from conversations — captures them to the brain."
version: 1.0.0
author: Your Company
tags: [gbrain, capture, enrichment]
---

# GBrain Signal Detector

Fires on every incoming message that contains substantive content. Captures TWO things
with EQUAL priority:

1. **Original thinking** — the user's ideas, observations, theses, frameworks
2. **Entity mentions** — people, companies, project names, concepts

Original thinking is AT LEAST as valuable as entity extraction. Ideas are the
intellectual capital. Entities are bookkeeping. Both compound over time.

## When to Use This Skill

Load this skill whenever:
- The user shares a substantive message, idea, or observation
- A conversation contains entity references you want to capture
- You're ending a conversation that generated useful content
- You see something that should be preserved in the company brain

**Do NOT** load this for purely operational messages (ok, thanks, greetings, single-word replies).

## Available Tools

Use gbrain MCP tools (prefixed with `mcp_gbrain_`):
- `mcp_gbrain_search` — check if entity page exists
- `mcp_gbrain_query` — semantic search for related context
- `mcp_gbrain_get_page` — load existing pages
- `mcp_gbrain_put_page` — create/update brain pages
- `mcp_gbrain_add_link` — cross-reference entities
- `mcp_gbrain_add_timeline_entry` — record events on entity timelines
- `mcp_gbrain_add_tag` — tag pages

Fallback CLI commands if MCP is unavailable:
```
gbrain search "entity name"
gbrain get "people/slug"
```

## Capture Rules

### Original Ideas
When the user expresses a novel thought, observation, or thesis:
1. Capture **exact phrasing** — the user's language IS the insight, don't paraphrase
2. File under `ideas/` or `concepts/` in the brain
3. Cross-link to related people, companies, and projects
4. Use `mcp_gbrain_add_link` to connect the page

### Entity Mentions
When a person, company, or project is mentioned:
1. `mcp_gbrain_search "name"` — does a page exist?
2. If NO page → check notability. If notable, create page
3. If page exists but thin → add new information
4. For new facts with specific dates → `mcp_gbrain_add_timeline_entry`

### Back-linking (MANDATORY)
Every time you create or update a brain page that references a person or company:
- Check if that entity has a brain page
- If yes → add a back-link FROM their page TO the page you just updated
- An unlinked mention is a broken brain

## Logging

After capturing, log a one-line summary:
> Signals: N ideas captured, N entities enriched, N timeline entries

## Anti-Patterns

- Blocking the main response to wait for signal detection
- Paraphrasing the user's original thinking instead of capturing exact phrasing
- Creating pages for non-notable entities (one-off mentions)
- Skipping back-links
- Running on purely operational messages (ok, thanks, do it)
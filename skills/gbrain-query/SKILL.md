---
name: gbrain-query
description: "Three-layer gbrain query pipeline: search → recall → think. Use for ALL brain queries instead of raw MCP calls."
version: 1.0.0
author: Your Company
tags: [gbrain, query, search, think]
---
# gbrain Query Pipeline

**The canonical way to get answers from gbrain.** Never use raw MCP tools directly — always follow this escalation ladder.

## The Three Layers

| Layer | Tool | When | Cost |
|-------|------|------|------|
| 1. Search | `mcp_gbrain_search` / `mcp_gbrain_query` | Simple fact lookup, find a page | Fast, zero LLM cost |
| 2. Recall | `mcp_gbrain_recall` | Recent events, session context, entity claims | Lightweight |
| 3. Think | `mcp_gbrain_think` | Complex synthesis, conflicts, gaps | Heavy (LLM synthesis) |

## The Escalation Ladder (MANDATORY)

Always start at Layer 1 and escalate only if insufficient:

1. **`mcp_gbrain_search(query, limit=5)`** — keyword search. Fast. If results have score >0.3, use them.
2. **`mcp_gbrain_query(query, limit=5)`** — hybrid semantic search when keyword is thin.
3. **`mcp_gbrain_recall(entity=<slug>, limit=20)`** — facts table for entity timeline.
4. **`mcp_gbrain_think(question)`** — multi-hop synthesis with citation + gap analysis. Only when you need synthesis across sources.

## Freshness Rules

- If a page was updated >90 days ago and the topic is time-sensitive, flag staleness.
- Always cite slug + date in output: `[[people/foo]]` (last updated 2026-03-15)
- Use `mcp_gbrain_get_versions(slug)` to check if a page has recent edits before declaring staleness.

## Entity-Specific Lookups

| Entity type | Primary page | Check |
|-------------|-------------|-------|
| Person | `people/<slug>` | get_page, timeline, links |
| Company | `companies/<slug>` | Same + financial/team data |
| Project | `projects/<slug>` | Timeline, tasks, decisions |
| Concept | `concepts/<slug>` or `ideas/<slug>` | Related pages, think |

## When NOT to query

- Pure operational tasks (cron, docker, file ops)
- User is asking you to *do* something, not *know* something
- The answer is in the current conversation context

## Pitfalls

- ❌ Starting with `mcp_gbrain_think` for simple fact lookups
- ❌ Skipping search and going straight to web/API
- ❌ Not citing brain sources in responses
- ❌ Ignoring staleness flags
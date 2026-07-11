---
name: gbrain-think
description: "Use gbrain's multi-hop synthesis layer to produce cited answers with conflict and gap analysis. Produces better answers than raw search."
version: 1.0.0
author: Your Company
tags: [gbrain, synthesis, query]
---

# GBrain Think — Synthesis Layer

gbrain's `think` operation is a multi-hop synthesis engine that:
1. Searches the brain (hybrid search)
2. Reads the top results
3. Composes a synthesized answer with explicit citations
4. Includes CONFLICT detection (when sources disagree)
5. Includes GAP analysis (what the brain doesn't know)

This produces significantly better answers than raw search for complex questions.

## When to Use

Use `mcp_gbrain_think` for:
- "What do we know about X?" — complex entity synthesis
- "Tell me about Y" — background briefings
- "Who is..." / "What happened..." — narrative questions
- "What's the status of..." — project/company updates
- Any question that needs synthesis across multiple brain pages

**Do NOT** use think for simple fact lookups (use `mcp_gbrain_search` instead).

## Usage via MCP (preferred)

Call the MCP tool directly:
```
mcp_gbrain_think(question="What do we know about X?")
```

Returns a structured answer with:
- `answer` — synthesized prose with inline citations
- `evidence` — list of source pages used
- `conflicts` — note when sources disagree
- `gaps` — what the brain doesn't know
- `warnings` — staleness flags

## Usage via CLI (fallback)

```
gbrain think "What do we know about X?"
```

## Parameters (MCP tool)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `question` | Yes | The question to think about |
| `anchor` | No | Pull entity subgraph around this slug |
| `rounds` | No | Multi-pass rounds (default 1) |
| `since` | No | Start of temporal window (YYYY-MM-DD) |
| `until` | No | End of temporal window |
| `model` | No | Model override |

## Chaining

For complex workflows, chain think with other tools:
1. Think → get synthesized answer with gap analysis
2. Search/web for the gaps the brain flagged
3. Write new info back to brain with `mcp_gbrain_put_page`

This fixes the brain's knowledge gaps autonomously.
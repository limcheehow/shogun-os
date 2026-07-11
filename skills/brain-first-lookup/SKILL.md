---
name: brain-first-lookup
description: "Mandatory brain-first lookup protocol: query gbrain before any external API call. Check brain for people, companies, entities before searching the web or other sources."
version: 1.1.0
author: Your Company
tags: [gbrain, lookup, protocol]
---

# Brain-First Lookup Protocol

**Read this before doing ANY entity/person/company/fact lookup.** This skill must be loaded
at the start of any task that involves looking up information about people, companies,
concepts, or facts.

## ⚠️ Critical Disambiguation: "gbrain skills" has TWO meanings

When someone says "gbrain skills", they could mean **either of two different things** —
resolving this incorrectly wastes turns:

| Meaning | What it is | Where to find it |
|---------|-----------|-----------------|
| **Hermes-agent skills about gbrain** | Agent-level Hermes skills like this one (`brain-first-lookup`), `gbrain-think`, `gbrain-signal-detector`, `brain-database-migration`, etc. | `~/.hermes/skills/` — loaded via skill_view(name) |
| **gbrain's own skillpack** (the gbrain repo's skills/) | The canonical workflow skills shipped with the gbrain project itself — `query`, `ingest`, `capture`, `enrich`, `maintain`, etc. | `github.com/garrytan/gbrain/skills/` — each is a `SKILL.md` subdirectory with triggers in YAML frontmatter |

**Rule**: When the user says "gbrain skills", default to meaning #2 (the gbrain repo skillpack) unless they explicitly say "Hermes skill", "Hermes gbrain skill", or name one by your known Hermes skill name. The gbrain repo is the source of truth for gbrain workflows.

See `references/gbrain-skillpack.md` for the full manifest and per-skill descriptions.

## The Hard Rule

**Always query gbrain BEFORE calling any external API** (web search, Slack, email, GitHub, etc.).

The brain has ~16,000 pages of company knowledge. The answer is almost always there.
External APIs are supplementary only.

## Available gbrain MCP Tools

Once the gbrain MCP server is connected, these tools are available with the `mcp_gbrain_` prefix:

| Tool | Use for |
|------|---------|
| `mcp_gbrain_search` | Keyword search — fast, zero API cost |
| `mcp_gbrain_query` | Hybrid semantic + keyword — best quality |
| `mcp_gbrain_get_page` | Read a full page when you know the slug |
| `mcp_gbrain_get_links` | Outgoing links from a page |
| `mcp_gbrain_get_backlinks` | Who references this entity |
| `mcp_gbrain_get_timeline` | Dated events for an entity |
| `mcp_gbrain_resolve_slugs` | Fuzzy slug resolution |
| `mcp_gbrain_traverse_graph` | Walk the relationship graph |
| `mcp_gbrain_put_page` | Create or update a brain page |
| `mcp_gbrain_think` | Multi-hop synthesis with citations + gap analysis |

If the MCP tools are not available, use the gbrain CLI directly via terminal:
`gbrain search "query"`, `gbrain think "question"`, `gbrain get <slug>`, `gbrain query "question"`

## The Lookup Chain (MANDATORY ORDER)

1. **`mcp_gbrain_search`** first — keyword search, fast, zero API cost
2. **`mcp_gbrain_query`** if search is thin — hybrid semantic search
3. **`mcp_gbrain_think`** for complex questions needing synthesis
4. **`mcp_gbrain_get_page`** if you found a slug — read full compiled truth
5. **External APIs only after steps 1-4 return nothing useful**

Never skip to external APIs without completing steps 1-2 at minimum.

## Quality Rules

- Score > 0.3 on search = use it. Don't reach for external APIs.
- User's direct statements in the brain are highest-authority data.
- Every brain page reference in output should cite the source slug.
- If brain info is stale, note the date but still cite it.
- Flag gaps: "The brain doesn't have information on X" rather than hallucinating.

## When Sub-agents Are Spawned

When delegating to sub-agents, include this line in their task prompt:
> Read the brain-first-lookup skill before starting work — query gbrain before any external API call.

## Exemptions

Pure operational tasks (file ops, docker, cron, server management) don't need brain-first lookup.
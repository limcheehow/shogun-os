---
name: search-router
description: Intelligent search router — analyzes query intent and routes to Exa (official/factual), last30days (community/sentiment), or both. Load before any research task.
category: research
tags: [search, router, exa, last30days, research]
---

# Search Router — Query Classification & Routing

Load this skill before any research task. Classify the query, then route to the right search backend.

## Decision Tree

```
QUERY → classify → route:
  ├─ FACTS     → Exa only
  ├─ OPINION   → last30days only
  └─ MIXED     → Both (run in parallel)
```

## Classification Rules

### FACTS → Exa

Query asks for objective, verifiable information. No opinion needed.

Triggers:
- Scores, results, standings ("Who won...", "score of...")
- Release notes, changelogs ("What's new in...", "v0.16.0 features")
- Documentation, specs ("How do I...", "API for...", "config option for...")
- Prices, dates, statistics ("When is...", "How much does...")
- Official statements, legal, compliance
- "What is X?" (definitional)

### OPINION → last30days

Query asks for subjective assessment, community consensus, or real user experience.

Triggers:
- "What do people think about..."
- Comparisons with subjective dimension ("vs" — which is better?)
- "Is X any good?" / "Should I use X?"
- "Best X for Y" (recommendations)
- "What's the buzz about..."
- Sentiment questions ("Are people excited about...")
- Cultural/trending topics ("Shakira's performance")
- Community reaction ("How did the community respond to...")

### MIXED → Both

Query has both factual and opinion components. Run in parallel.

Triggers:
- Product research ("X pricing AND reviews")
- Event coverage ("World Cup scores AND fan reaction")
- Tech evaluation ("Claude Code features AND developer sentiment")
- "Tell me about X" (broad — needs both facts and community take)
- Any query where "give me everything" is implied

## Implementation

### Exa path
```
web_search(query, limit=5)
web_extract on top 2-3 results for depth
```

### last30days path
```bash
cd /tmp/last30days-skill/skills/last30days
python3.12 scripts/last30days.py "QUERY" --search=reddit,hackernews --emit=compact
```
For named entities, generate a `--plan` JSON first (see Step 0.75 in the last30days SKILL.md):
```bash
QUERY_PLAN=$(cat << 'PLANEOF' > /tmp/last30days-plan.json
{
  "intent": "concept|person|product|breaking_news",
  "freshness_mode": "strict_recent|recent_or_evergreen|evergreen_ok",
  "cluster_mode": "story|none|comparison",
  "subqueries": [
    {"label": "primary", "search": "paraphrased query 1"},
    {"label": "reaction", "search": "paraphrased query 2"}
  ]
}
PLANEOF
)
python3.12 scripts/last30days.py "QUERY" --plan /tmp/last30days-plan.json --emit=compact
```

### Parallel execution
For MIXED queries, fire both simultaneously (no dependency between them):
- Exa returns in ~2s
- last30days returns in ~5-35s
- Present results side-by-side with source attribution

## Query Examples from Testing

| Query | Classification | Why |
|---|---|---|
| "Hermes Agent v0.16.0 features" | FACTS → Exa | Release notes, changelog |
| "World Cup scores today" | FACTS → Exa | Live results, objective |
| "Cursor vs Copilot which is better" | OPINION → last30days | Subjective comparison |
| "What devs think about Hermes Agent" | OPINION → last30days | Community sentiment |
| "World Cup 2026" | MIXED → Both | Scores + cultural reaction |
| "Hermes Agent pricing and reviews" | MIXED → Both | Facts + sentiment |
| "Is Claude Code worth it?" | OPINION → last30days | Subjective recommendation |
| "How to configure api_max_retries" | FACTS → Exa | Documentation lookup |

## Anti-Patterns

- Do NOT use last30days for documentation lookups (waste of time, wrong results)
- Do NOT use Exa for "what's the community saying" (returns blog posts, not real users)
- Do NOT run both for trivial factual queries ("when was X released?")
- For MIXED queries, do NOT describe what you'll do — just run both in parallel
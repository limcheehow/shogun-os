---
name: gbrain-idea-ingest
description: "Structured ingestion of links, articles, tweets, and web content into gbrain — extract entities, write summary, cross-link to known people/companies/projects."
version: 1.0.0
author: user
tags: [gbrain, ingest, ideas, links, articles]
---
# gbrain Idea Ingest

Ingest external ideas — links, articles, tweets, blog posts — into the brain with entity extraction, summary, and cross-linking.

## When to Use

- User shares a link and says "save this" or "ingest this"
- You find an article/blog/tweet relevant to a brain topic
- A conversation surfaces a useful external resource
- Competitive intel, industry news, research papers

## Pipeline

1. **Fetch content** — `web_extract` or `browser_navigate` to read the page
2. **Extract key info** — title, author, date, main points, entities mentioned
3. **Summarize** — 2-3 sentence summary + key takeaways (bullet points)
4. **Entity extraction** — scan for people, companies, projects, concepts
5. **Brain check** — search each entity against gbrain
6. **Write** — create page under `references/<topic>/` or `ideas/`
7. **Cross-link** — link from each entity TO the new page
8. **Timeline** — if the content references a dated event, add timeline entry

## Page Template

```yaml
---
title: "Article: [Title of the piece]"
type: reference
tags: [reference, <topic>]
source: "https://..."
ingested: "2026-06-10"
author: "Author name"
---

## Summary
2-3 sentence summary of the content.

## Key Points
- Point 1
- Point 2
- Point 3

## Entities
- [[people/someone]] — mentioned in context of X
- [[companies/some-company]] — discussed in section Y

## Relevance
Why this matters — connection to existing brain topics.
```

## Cross-Linking Rules

- Every known entity mentioned in the content gets a back-link from their page TO the new reference page
- Use `mcp_gbrain_add_link(from=entity_slug, to=idea_slug, context="mentioned in")`
- For new (unknown) entities, create a minimal stub first

## Pitfalls

- ❌ Long copy-paste without summary (brain prefers condensed knowledge)
- ❌ Skipping entity cross-links (content becomes an island)
- ❌ Filing under wrong path (articles → `references/`, not `people/`)
- ❌ Ingestion without dedup check (search first!)
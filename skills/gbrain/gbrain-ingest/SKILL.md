---
name: gbrain-ingest
description: "Ingest URLs, files, and documents into gbrain — auto-detect type, extract entities, file correctly, cross-link."
version: 1.0.0
author: user
tags: [gbrain, ingest, import, file]
---
# gbrain Ingest Pipeline

Import external content into the brain with proper filing, entity extraction, and cross-linking.

## Ingestion Types

| Type | Pipeline | Brain path |
|------|----------|-----------|
| URL / article | Fetch → extract → summarize → entity-link | `references/<topic>/` |
| PDF document | OCR/extract → key points → entity-link | `references/<topic>/` or `projects/<project>/` |
| Image/screenshot | Describe → extract text → entity-link | `references/<topic>/` |
| Code/file | Read → summarize purpose → link to project | `projects/<project>/` |
| Email thread | Extract decisions → action items → entity-link | `conversations/` or `decisions/` |
| **Bulk directory** | `gbrain import <dir> --no-embed --workers N` | CLI-driven, 500+ files |

## Standard Pipeline

1. **Fetch/read** the content
2. **Detect type** — article, document, code, email, image
3. **Extract** — key facts, entities (people, companies, projects), dates, decisions
4. **Check brain** — `mcp_gbrain_search` each entity to see if pages exist
5. **Write** — create page using `mcp_gbrain_put_page` under the correct path
6. **Cross-link** — `mcp_gbrain_add_link` from entities TO the new page (back-links)
7. **Timeline** — `mcp_gbrain_add_timeline_entry` for dated events

## Page Structure

```yaml
---
title: "Title"
type: reference  # reference | decision | conversation | research
tags: [tag1, tag2]
source: "https://..."
ingested: "2026-06-10"
---
```

## Entity Extraction Rules

- Scan for every person, company, and project name
- Resolve each against the brain with `mcp_gbrain_search`
- Link new page back to each known entity
- If an entity is not in the brain, create a minimal stub page

## Pitfalls

- ❌ Writing to wrong brain path (check brain taxonomist if unsure)
- ❌ Skipping entity extraction for long-form content
- ❌ Not back-linking — orphaned content is invisible
- ❌ Duplicate pages (search before create)
- ❌ For email ingest specifically: the full pipeline is Gmail → collect-gmail-team.py → markdown files → gbrain import. See `references/email-pipeline.md` for the complete architecture, memory constraints, and batching strategy.
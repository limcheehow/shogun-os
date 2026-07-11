---
name: timeline-inject-v2
description: "Inject ## Timeline sections with gbrain-compatible format: - **YYYY-MM-DD** | Source — Summary. For companies and people pages."
version: 2.0.0
author: Your Company
tags: [brain, timeline, gbrain]
---

# Timeline Injector v2

Injects `## Timeline` sections into company and people pages using the EXACT format `gbrain extract timeline` parses.

## Critical Format

```markdown
## Timeline
- **2026-05-11** | frontmatter — First encountered in brain
- **2014-01-01** | frontmatter — Company founded
```

The extractor (`~/gbrain/src/commands/extract.ts` line 277) parses:
```typescript
/^- \*\*(\d{4}-\d{2}-\d{2})\*\*\s*\|\s*(.+?)\s*[—–-]\s*(.+)$/gm
```

So the format must be:
- **YYYY-MM-DD** | Source — Summary

## Run

```bash
# Dry run
python3 /tmp/timeline-inject-v2.py

# Apply
python3 /tmp/timeline-inject-v2.py --apply

# Then extract
cd ~/brain
gbrain extract timeline
gbrain extract all
```

## Results from 2026-06-21 Campaign

| Entity | Pages with dates | Entries extracted |
|--------|:---:|:---:|
| Companies | 284 | ~20 |
| People | 99 | ~6 |
| **Total** | **383** | **26** |

## Why Entries Are Limited

1. `gbrain extract timeline` deduplicates against existing DB entries
2. 4,928/5,213 companies have no date frontmatter (stub pages)
3. Timeline coverage compounds naturally over time as meetings, deals, and emails get linked

## Automatic Timeline Sources

The following already add timeline entries continuously:
- `sync-deal-activity.py` — adds `## Timeline` to deal/project pages when new emails arrive
- `gbrain extract timeline` — backlinks from wikilinks create timeline entries
- Meeting classifier — adds meeting entries to company/person pages

## Pitfalls

- ❌ **Format matters**: plain `- YYYY-MM-DD | text` won't extract. Must be `- **YYYY-MM-DD** | Source — Summary`
- ❌ **Deduplication**: `gbrain timeline-add` (CLI) and `## Timeline` sections both create DB entries. If you run both, the extractor skips duplicates
- ❌ **Incremental**: extract only processes changed files. Force full re-extract if needed
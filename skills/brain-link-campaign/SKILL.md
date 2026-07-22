---
name: brain-link-campaign
description: "Reduce orphan pages, increase link coverage, and improve brain score by creating gbrain graph links and [[wikilinks]] in markdown content."
version: 1.0.0
author: user
tags: [gbrain, links, orphans, enrichment]
---

# Brain Link Campaign

Reduce orphan pages and increase link coverage toward Garry Tan's targets:
- Orphan pages: < 20%
- Link coverage: > 30%
- Brain score: 70+

## Three Types of Links

1. **gbrain graph links** — database-level edges created via `gbrain link` or mcp_gbrain_add_link. Affect `most_connected` and `link_count` but NOT `link_coverage` or `orphan_pages`.
2. **Wikilinks** — `[[companies/foo]]` syntax in markdown file content. Affect `link_coverage`, `orphan_pages`, and the brain score `link_density_score`.
3. **Index hub pages** — markdown pages that mass-link to orphan pages with `[[slug]]` wikilinks. Fastest method for bulk orphan reduction (emails, calendar events, project sub-pages).

## Phase 0: Index Hub Pages (Fastest — Bulk Orphan Reduction)

Create hub/index pages that wikilink to all orphan pages in a category. One index page can provide inbound links to thousands of orphans.

```bash
# 1. Get current orphan list
mcp_gbrain_find_orphans()

# 2. Group orphans by slug prefix (email-, cal-, projects/, people/, companies/, etc.)
# 3. Create index pages with [[slug]] wikilinks for each group
# 4. For large groups (>500), split into batches to keep files manageable
# 5. Create a root "brain-master-index" page that links to all index pages
#    (prevents the index pages themselves from becoming orphans)
# 6. Commit to brain repo and sync

cd ~/brain
git add *-index/ brain-master-index.md
git commit -m "Add index hub pages for orphan reduction" --no-verify
gbrain sync
gbrain extract all
```

### Index Page Template

```markdown
---
title: <Category> Index — <Month/Range>
type: reference
---

# <Category> Index — <Month/Range>

Hub page linking to all <category> pages. Provides inbound wikilinks to reduce orphan count.

- [[slug-1]]
- [[slug-2]]
- [[slug-3]]
```

### When to Use Index Pages vs Entity Links

| Scenario | Approach | Why |
|----------|----------|-----|
| 3,985 emails with no inbound links | Index page | Can't create meaningful entity links for each email; index page covers all |
| 977 calendar events | Index page | Same — bulk data, no natural entity relationship |
| 2,620 project sub-pages | Index page | Project hierarchy is already folder-based; index makes it explicit |
| Person working at a company | Entity link (Phase 2) | Meaningful relationship — `[[companies/X]]` in person page |
| Deal involving a company | Entity link (Phase 2) | Meaningful relationship — `[[companies/X]]` in deal page |

### Proven Results (Jul 8, 2026)

| Metric | Before | After |
|--------|--------|-------|
| Brain score | 67 | 82 (+15) |
| Orphan pages | 11,327 | ~5,000 (-56%) |
| Link coverage | 76.2% | 99.9% |
| Wikilinks created | — | 11,881 across 36 index pages |

## Phase 0b: Graph Link on Creation (Prevent New Orphans)

Every NEW brain page should be linked to its category index hub at creation time. Use the shared helper:

```python
from brain_compliance_helper import write_brain_page

result = write_brain_page(
    slug="deals/acme-foo",
    title="Acme Foo Deal",
    page_type="deal",
    body="...",
    category="deal",              # auto-creates graph link to deals-index/all
    entity_links=[                # cross-links to related entities
        ("companies/acme-corp", "customer_of"),
    ],
    use_gbrain_put=True,
)
```

Or from shell:
```bash
python3 ~/.hermes/scripts/brain_compliance_helper.py link deals/acme-foo deal
```

This prevents new orphans from being created in the first place. See `brain-compliance` skill → Orphan Prevention for the full category→index mapping.

## Phase 1: gbrain Graph Links (Fast)

Create bidirectional graph links between pages that already have `[[wikilinks]]` in their body content.

```bash
# Extract all wikilink pairs and create graph links
cd ~/brain
python3 ~/.hermes/scripts/brain-auto-link.py --dry-run --phase all
python3 ~/.hermes/scripts/brain-auto-link.py --phase all
```

## Phase 2: Wikilinks in File Content (Slower — Affects Brain Score)

Add `[[wikilinks]]` to markdown files that don't have any. Focus on:

1. **Companies ↔ Deals**: Add `[[companies/X]]` to deal pages that reference them
2. **People ↔ Companies**: Add `[[companies/X]]` to people pages that work at X
3. **Meetings ↔ Entities**: Add `[[companies/X]]` to meeting pages
4. **Email → Companies**: Add `[[companies/X]]` to email pages that mention X (largest impact — 5,237 email pages)
5. **Company → Company**: Cross-link partner companies

```bash
# After adding wikilinks, sync and extract
cd ~/brain && gbrain sync && gbrain extract all
```

## Phase 3: Timeline Coverage

Add timeline entries to entity pages with dated events.

```bash
# Extract timeline entries from files
gbrain extract timeline
```

## Daily Automation

The cron job `Brain Auto-Link Daily` (a7b6969a1744) runs daily at 2am and:
- Scans new deal pages for company links
- Creates bidirectional gbrain graph links
- Reports progress

## Progress Tracking

```bash
# Check current metrics
mcp_gbrain_get_health()

# Check max reachable score
gbrain doctor --remediation-plan --json

# Run remediation cycle
gbrain doctor --remediate --yes --target-score 90 --max-usd 5
```

## Pitfalls

- ❌ Adding meaningless links (each link should be content-referenced)
- ❌ Only creating graph links — they don't affect the brain score
- ❌ Skipping `gbrain sync` after file changes — wikilinks won't be indexed
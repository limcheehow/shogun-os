# Brain Compliance Guide

> **Ensuring every brain page is compliant, cross-linked, and non-orphan.**
> A 3-layer enforcement architecture: Agent Gate → Pre-Commit Hook → Batch Audit.

---

## The Problem

Without enforcement, brain pages accumulate issues:
- Missing `title:` or `type:` frontmatter
- Bare wikilinks (`[[Eddie]]` instead of `[[people/eddie-goh|Eddie]]`)
- Orphan pages with no inbound links (drag down brain score)
- Slug convention violations (uppercase, underscores, spaces)

## The Solution: 3-Layer Architecture

```
NEW BRAIN PAGE CREATED
        │
        ▼
┌─────────────────────────────────────┐
│ LAYER 1: Agent Gate                 │
│ Loads brain-compliance skill        │
│ brain_compliance_helper.py enforces │
│ Runs validator as final step        │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ LAYER 2: Pre-Commit Hook            │
│ ~/brain/.git/hooks/pre-commit       │
│ Validates ALL staged .md files      │
│ Blocks commit on violations         │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ LAYER 3: Batch Audit (manual)       │
│ python3 validator --batch           │
│ Full brain scan for drift           │
│ Run weekly or on-demand             │
└─────────────────────────────────────┘
```

### Layer 1: Agent Gate

Every brain-writing script and cron job should use `brain_compliance_helper.py`:

```python
from brain_compliance_helper import write_brain_page

result = write_brain_page(
    slug="deals/acme-foo",
    title="Acme Foo Deal",
    page_type="deal",
    body="Deal content...",
    category="deal",                    # auto-links to deals-index/all
    entity_links=[                      # cross-links to related entities
        ("companies/acme-corp", "customer_of"),
    ],
    use_gbrain_put=True,                # sync to DB immediately
)
```

**Key features:**
- ✅ YAML frontmatter (title, type, tags — auto-adds type as tag)
- ✅ # H1 heading matching frontmatter title
- ✅ Slug validation (lowercase, hyphens, no underscores)
- ✅ Graph link to category index hub (orphan prevention)
- ✅ Entity cross-linking (bidirectional)
- ✅ Post-write validation

### Layer 2: Pre-Commit Hook

`~/brain/.git/hooks/pre-commit` validates every staged `.md` file:

```bash
# Blocks commits with violations:
❌ concepts/bad-page.md
     • MISSING: 'title:' field in frontmatter
     • WIKILINK: [[Eddie]] uses bare display name

# Allows compliant commits:
✅ 1/1 files compliant — commit allowed
```

Emergency bypass: `git commit --no-verify`

### Layer 3: Batch Audit

```bash
python3 ~/.hermes/skills/brain-compliance/scripts/validate-brain-page.py ~/brain --batch
```

---

## Category → Index Mapping

| Category | Index hub slug | Dynamic? |
|----------|---------------|----------|
| deal | `deals-index/all` | No |
| email | `email-index/YYYY-MM-w1` (current half-month) | Yes |
| meeting | `meetings-index/all` | No |
| scrum | `scrum-index/all` | No |
| person | `people-index/batch-NN` | Yes |
| company | `companies-index/batch-NN` | Yes |
| ticket | `projects/support_tickets/all-tickets` | No |
| calendar | `cal-index/YYYY-MM` (current month) | Yes |
| project | `projects/active_projects/all-pages` | No |
| note | `notes-index/all` | No |
| hr | `hr-index/all-hr` | No |
| concept | `concepts-index/all` | No |
| idea | `ideas-index/all` | No |

---

## Environment Variables

The helper script respects these env vars:

| Env Var | Default | Purpose |
|---------|---------|---------|
| `BRAIN_DIR` | `~/brain` | Root brain directory |
| `GBRAIN_BIN` | `~/.local/bin/gbrain` | gbrain CLI path |
| `BRAIN_VALIDATOR` | `~/.hermes/skills/brain-compliance/scripts/validate-brain-page.py` | Validator script path |

---

## Related Skills

- **`brain-compliance`** — The skill that teaches agents to write compliant pages
- **`brain-link-campaign`** — Bulk orphan reduction via index hub pages
- **`gbrain-operations`** — Core gbrain read/write operations
- **`brain-first-lookup`** — Always query gbrain before writing

## Related Recipes

- [`recipes/brain-maintenance.md`](../recipes/brain-maintenance.md) — Regular brain health maintenance
- [`recipes/drive-to-brain.md`](../recipes/drive-to-brain.md) — Syncing Google Drive docs to brain
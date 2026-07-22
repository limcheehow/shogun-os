---
name: brain-compliance
description: >-
  Standards and validation for Gbrain-compliant brain pages.
  Mandatory to load whenever writing, editing, or creating brain files.
version: 1.1.0
author: user
tags: [brain, gbrain, compliance, standards]
triggers:
  - "create brain page"
  - "write brain file"
  - "add person"
  - "add company"
  - "add deal"
  - "save to brain"
  - "enrichment"
  - "brain compliance"
  - "validate brain"
  - "check compliance"
---

## Your Company Conventions

| Convention | Your Company | Gbrain Standard |
|-----------|--------|-----------------|
| Person folder | `people/` | `persons/` |
| Primary classifier | `type: company` | `tags: [company]` |
| HR folder (unified) | `hr/` | N/A |
| Canonical types | 14 types | arbitrary |
| Email storage | `data/email/` | N/A |
| Product dev | `products/your-product/`, `products/your-product-v2/` | N/A |

The validator accepts BOTH `type:` and `tags:` as valid classifiers.

## 14 Canonical Types

`company`, `person`, `project`, `project-scrum`, `deal`, `meeting`, `product-scrum`, `note`, `email`, `concept`, `calendar-event`, `hr`, `ticket`, `status-report`

---

## 1. Per-Entity Type Frontmatter Standards

### people/ (`people/<slug>.md`)

```yaml
---
type: person                    # OR tags: [person, contact]
title: "Full Name"
first_seen: YYYY-MM-DD
source: meeting|email|nrf|linkedin|cold-call|referral
company: Company Name
role: Job Title
email: person@company.com
phone: "+601****6789"          # optional
linkedin: https://linkedin.com/in/...  # optional
---
```

- `title:` must match the first `# Heading` in the file
- Slug must be lowercase, hyphenated: `eddie-goh.md`, not `Eddie Goh.md`
- Wikilinks to this person always use `[[people/eddie-goh|Eddie Goh]]`

### companies/ (`companies/<slug>.md`)

```yaml
---
type: company                   # OR tags: [company, customer]
title: "Company Name"
tags: [company, customer]
industry: Retail / Technology / ...
first_seen: YYYY-MM-DD
source: meeting|email|nrf|web|referral
website: https://www.example.com
domain: example.com           # optional
email_domain: "@example.com"  # optional
type: customer|vendor|partner|competitor|potential-customer  # optional
---
```

### deals/ (`deals/<slug>.md`)

```yaml
---
type: deal                      # OR tags: [deal]
title: "Deal Name"
tags: [deal]
stage: Lead|Qualified|Proposal|Negotiation|Closed Won|Closed Lost
owner: Sales Rep Name
customer: Customer Company Name
partner: Partner Name
industry: Retail / Technology / ...
amount: 123456.78
mrr: 0
contact_name: Contact Person
contact_email: contact@company.com
relationship: partner > customer > your-company
close_date: YYYY-MM-DD
priority: High|Medium|Low
hot: true|false
created: YYYY-MM-DD
deal_id: ""                   # optional
lead_source: referral|event|cold-call|inbound  # optional
---
```

### daily/ pages (`daily/<YYYY-MM-DD>.md` or `daily/<subtype>/YYYY/MM/<YYYY-MM-DD>.md`)

```yaml
---
title: "Daily Log — YYYY-MM-DD (Monday)"   # or "Briefing — YYYY-MM-DD"
type: daily|morning-briefing|email-digest|task-snapshot|calendar
date: YYYY-MM-DD
weekday: Monday               # optional
tags: [daily, log]            # or [daily, briefing, news] for briefings, [daily, financial, weekly] for financial
---
```

### meetings/ (`meetings/YYYY/MM/<title>.md`)

```yaml
---
title: "Meeting Title"
type: meeting
date: YYYY-MM-DD
source: google-calendar|outlook|manual
source_id: "<calendar-event-id>"
tags: [meeting]
---
```

### wiki/ pages (`wiki/<section>/<slug>.md`)

```yaml
---
title: "Page Title"
tags: [wiki, <section>]
---
```

---

## 2. Filename Rules (ALL entity types)

| Rule | ✅ Correct | ❌ Wrong |
|------|-----------|---------|
| Lowercase | `eddie-goh.md` | `Eddie Goh.md` |
| Hyphens, no spaces | `alvin-ong.md` | `Alvin Ong.md` |
| No special chars | `1-utama-shopping-centre.md` | `1 Utama Shopping Centre.md` |
| Folder prefix in wikilinks | `[[people/eddie-goh\|Eddie]]` | `[[Eddie]]` |

---

## 3. Wikilink Rules

- **Always** use `[[folder/slug|Display Name]]` format
- Our injected wikilinks use `[[companies/foo]]` (no display name) — valid
- **Never** use bare display names like `[[Eddie]]` — they don't resolve
- Existing bare-name links (like `[[Kossan]]`) should be fixed to `[[companies/kossan|Kossan]]`
- Cross-link related entities: person to company, company to deals, deal to contacts

### Orphan Prevention (Mandatory for Scripts)

Every brain-writing script MUST ensure new pages have at least one inbound graph link. Without this, pages become orphans and drag the brain score down.

**Standard implementation — use the shared helper:**

```python
from brain_compliance_helper import write_brain_page

result = write_brain_page(
    slug="deals/acme-foo",
    title="Acme Foo Deal",
    page_type="deal",
    body="Deal content...",
    tags=["test"],
    extra_fields={"stage": "Lead", "customer": "Acme Corp", "created": "2026-07-08"},
    category="deal",                      # auto-links to deals-index/all
    entity_links=[                         # cross-links to related entities
        ("companies/acme-corp", "customer_of"),
        ("people/john-doe", "attended"),
    ],
    use_gbrain_put=True,                   # sync to DB immediately
)
# result = {"slug", "filepath", "valid", "links_created", "warnings"}
```

The helper handles:
1. ✅ YAML frontmatter (title, type, tags — auto-adds type as tag)
2. ✅ # H1 heading matching frontmatter title
3. ✅ Slug validation (lowercase, hyphens, no underscores)
4. ✅ Graph link to category index hub (orphan prevention)
5. ✅ Entity cross-linking (bidirectional graph links)
6. ✅ Post-write validation via brain-compliance validator

**For shell scripts:**
```bash
# Write page, then link to index
gbrain put deals/acme-foo --content "$(cat file.md)"
python3 ~/.hermes/scripts/brain_compliance_helper.py link deals/acme-foo deal
```

**For agent skills (MCP):**
```python
mcp_gbrain_put_page(slug, content)
mcp_gbrain_add_link(from="deals-index/all", to=slug,
                     link_type="mentions", link_source="script-auto")
```

**Category → Index mapping:**

| Category | Index hub slug |
|----------|---------------|
| deal | deals-index/all |
| email | email-index/YYYY-MM-w1 (current half-month) |
| meeting | meetings-index/all |
| scrum | scrum-index/all |
| person | people-index/batch-NN (current batch) |
| company | companies-index/batch-NN |
| ticket | projects/support_tickets/all-tickets |
| calendar | cal-index/YYYY-MM (current month) |
| project | projects/active_projects/all-pages |
| note | notes-index/all |
| hr | hr-index/all-hr |
| concept | concepts-index/all |
| idea | ideas-index/all |

**Validator check:** The pre-commit hook validates frontmatter and wikilink format, but does NOT check for orphan status. Run `mcp_gbrain_find_orphans()` periodically to catch pages that slipped through.

---

## 4. Post-Write Validation

**Two approaches — use gbrain MCP when possible:**

### A. gbrain-Native Validation (Preferred)

After every `mcp_gbrain_put_page` call, verify the page is indexed and compliant:

```python
# Verify page was indexed
result = mcp_gbrain_search(query="slug:<slug>")
assert result.count > 0, "Page not indexed!"

# Check schema compliance
mcp_gbrain_schema_lint(pack="active")

# Run brain health check
mcp_gbrain_get_health()

# List recent pages to verify type
mcp_gbrain_list_pages(type="employee", limit=5)
```

### B. File-Based Validator (Legacy Fallback)

For existing files or when gbrain is unavailable:

```bash
# Single file mode
python3 ~/.hermes/skills/brain-compliance/scripts/validate-brain-page.py ~/brain/persons/eddie.md

# Batch scan a whole folder
python3 ~/.hermes/skills/brain-compliance/scripts/validate-brain-page.py ~/brain/persons/ --batch

# JSON output for programmatic reporting
python3 ~/.hermes/skills/brain-compliance/scripts/validate-brain-page.py ~/brain/ --batch --json
```

If violations are reported, fix them before delivering the result to the user.

**Validator checks performed:**
1. **Frontmatter** — valid YAML, `title:` present, no unquoted `@` values
2. **Tags** — correct `tags_must_contain` for the entity type (e.g. `person` for `people/`)
3. **Required fields** — all mandatory fields present per entity type
4. **Slug** — lowercase, hyphenated format
5. **Heading** — at least one `# level-1 heading` in the body
6. **Wikilinks** — no bare display names (single-file mode only)
7. **Title/heading match** — `title:` field matches first `# Heading`

---

## 5. Enforcement Architecture (3 Layers)

```
NEW BRAIN PAGE CREATED
        │
        ▼
┌─────────────────────────────────────┐
│ LAYER 1: Agent Gate (me + cron agents) │
│ Loads brain-compliance skill         │
│ Runs validator as final step         │
│ ✅ 5 cron jobs wired                 │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ LAYER 2: Pre-Commit Hook             │
│ ~/brain/.git/hooks/pre-commit        │
│ Validates ALL staged .md files       │
│ Blocks commit on violations          │
│ ✅ Catches script-generated pages    │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ LAYER 3: Batch Audit (manual)        │
│ python3 validator --batch            │
│ Full brain scan for drift            │
│ ✅ Run weekly or on-demand           │
└─────────────────────────────────────┘
```

### Layer 1: Agent Gate

Brain-writing crons load `brain-compliance` skill + validate as final step:

| Cron | Folder | Skills |
|------|--------|--------|
| Sales CRM Pipeline | `deals/` | `brain-compliance` |
| Candidate Application Pipeline | `HR/`, `hr/` | `brain-compliance` + 3 |
| Hiring Pipeline Daily | `HR/`, `hr/` | `brain-compliance` |
| Meeting Brain Classifier | `meetings/` | `brain-compliance` |
| Collect Calendar | `data/calendar/` | `brain-compliance` |

### Layer 2: Pre-Commit Hook

`~/brain/.git/hooks/pre-commit` validates every staged `.md` file before commit:

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

## 6. Cron Jobs — Post-Write Requirement

Every cron job that writes a brain page MUST include a "Validate Compliance" step after the write step. Use this pattern:

```markdown
### Final Step: Validate Compliance
Run the compliance check using gbrain MCP tools (preferred) or the local validator:
```bash
# Preferred: gbrain-native validation
mcp_gbrain_get_health
mcp_gbrain_schema_lint(pack="active")

# Alternative: if gbrain unavailable, run the validator
python3 ~/.hermes/skills/brain-compliance/scripts/validate-brain-page.py ~/brain/path/to/file.md
```
If any violations are reported, fix them.
```

---

## Pitfalls

- ❌ **Don't skip frontmatter** — every brain file needs at least `title:` and `tags:`
- ❌ **Don't use bare wikilinks** — always `[[folder/slug|Display]]`
- ❌ **Don't create files with uppercase or spaces in filenames**
- ❌ **Don't skip the post-write validation** — run it every time
- ❌ **Don't write person/company/deal files to wrong folders** — each type has a dedicated folder
- ❌ **Don't skip orphan prevention** — new pages without inbound links drag the brain score down
- ❌ **Don't use `link_source` values `markdown`, `frontmatter`, `mentions`, or `wikilink-resolved`** — these are reserved by gbrain and will be rejected
# CSV Batch Enrichment

When a conference/event yields a CSV of contacts (name, company, title, LinkedIn URL, priority), enrich them in batch rather than one-by-one.

## Workflow

### Step 1: Prepare contacts list

Parse the CSV and identify:
- Which contacts are **already in brain** (check `~/brain/persons/`) — skip or just add timeline entry
- Which are **new** — need full enrichment
- Priority order (High → Medium)

### Step 2: Web research for context (run first)

For each new contact, especially high-profile ones (CIO, CTO, CDO, MD at large retailers):
```
web_search "First Last Company role"
```

This catches:
- Role confirmation / discrepancies from what the CSV says
- Recent news (promotions, hiring, conference speaking)
- Company background (industry, size)

### Step 3: Apollo enrichment for structured data

Apollo.io provides verified emails and phone numbers. This is the fastest way to fill structured gaps.

**Person matching:**
```bash
curl -s "https://api.apollo.io/api/v1/people/match" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "First", "last_name": "Last", "organization_name": "Company"}'
```

Returns: email (verified/unverified status), phone, title, city/country, LinkedIn URL, employment history.

**Company enrichment:**
```bash
curl -s "https://api.apollo.io/api/v1/organizations/search" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q_organization_name": "Company Name", "per_page": 1}'
```

Returns: website, industry, employee count, phone, founded year, LinkedIn URL, stock ticker.

⚠️ **The Apollo key lives in `~/.bashrc`** — source it before use. Key length is ~22 chars.

### Step 4: Create person files

Each contact gets their own file at `~/brain/persons/<slug>.md` with frontmatter:
```yaml
---
tags: [person, contact, event-name]
email: person@company.com
phone: +60XX
company: Company Name
role: Job Title
linkedin: https://linkedin.com/in/username
first_seen: YYYY
source: event-name
---
```

### Step 5: Create company files (if new)

Check `~/brain/companies/` first. Create if absent.

### Step 6: Add timeline entry

```
- YYYY-MM-DD | NRF Big Show APAC 2026 contact — {title}, {company}. [Source: NRF conference contacts list]
```

## Key Lessons

- **Slug collision checking**: Before creating person files, scan `~/brain/persons/` for partial name matches. Many names repeat across events.
- **Data quality**: CSV titles are often abbreviated or out of date. Apollo's `people/match` returns the current title — prefer it over the CSV.
- **Name normalization**: Apollo `people/match` is sensitive to first_name + last_name + organization_name combination. Try alternate spellings if the first attempt returns nothing.
- **Rate limits**: Space Apollo calls ~500ms apart. Batch with a sleep between each.
- **Missing Apollo hit**: ~40-60% of contacts may return no data from Apollo (small/private companies, unusual names). This is normal — accept the gap rather than spending time on alternatives.
- **Sustainable pace**: 25 contacts at ~30 seconds each (web search + Apollo + file write) takes ~15 minutes. Break into batches of 8-12 for readability.

## Subagent Batch Size Limits

When using `delegate_task` to batch-enrich contacts, keep each batch to **7-12 contacts maximum**. Larger batches (21+) hit the 600s subagent timeout and lose all work.

**Pacing for 63-contact conference lists:**
- Batch A: 19 contacts → ✅ completes (~190s)
- Batch B: 21 contacts → ❌ times out at 600s (lost all work)
- Recovery: split the timed-out batch into groups of 7

**Optimal batch size by approach:**
| Method | Max batch | Reason |
|--------|-----------|--------|
| Manual (terminal + write_file) | 20-30 | No timeout, direct control |
| delegate_task (subagent) | 7-12 | 600s timeout limit |
| execute_code | 15-25 | 5-min limit, no web_search |

For large conferences (50+ contacts), prefer 2-3 parallel delegate_task calls of 7-12 contacts each, or run directly with terminal tools in a script.
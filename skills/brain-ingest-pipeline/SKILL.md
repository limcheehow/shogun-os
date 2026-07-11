---
name: brain-ingest-pipeline
description: "Unified brain ingest pipeline for email, calendar, and meetings — all three follow the same COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE flow."
version: 1.0.0
tags: [brain, ingest, pipeline, email, calendar, meetings]
triggers:
  - "brain ingest"
  - "pipeline"
  - "run pipeline"
  - "process emails"
  - "process calendar"
  - "gmail triage"
  - "collect calendar"
  - "entity extraction"
  - "link people"
  - "enrich profiles"
  - "validate brain"
  - "brain compliance"
  - "SA-DWD"
  - "batch rotation"
---

# Brain Ingest Pipeline — Unified

**All three ingest sources follow this exact flow. No exceptions.**

```
COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE
```

## Source Mapping

| Source | Cron Job | Collect Script |
|--------|----------|---------------|
| Email | gmail-triage (1 job, sequential batches via delegate_task) | `gmail-triage.py` |
| Calendar | Collect Calendar to gbrain | `collect-calendar-cron.sh` → `collect-calendar.py` |
| Meetings | Collect Meetings to gbrain | `collect-meetings.py` |

## Email Batch Config

Account batches are defined in `~/.hermes/config/gmail-batches.json`:
```json
{
  "batches": [
    ["your-user@your-domain.com", "hana@your-domain.com", "sarah@your-domain.com"],
    ["kunna@your-domain.com", "anwar@your-domain.com", "liyana@your-domain.com"],
    ["syazwan@your-domain.com", "fitri@your-domain.com", "iskandar@your-domain.com", "ashraf@your-domain.com"]
  ]
}
```
Edit this file to add/remove accounts. No script changes needed. The cron prompt reads the config dynamically.

## Phase 1: COLLECT

Run the source-specific collection script. This pulls raw data into `~/brain/data/<source>/` as markdown. Do NOT modify this phase — just run the script.

## Phase 2: ROUTE

For each new page created, classify and route:

| Signal | Action |
|--------|--------|
| **Sales / CRM** — deal names, client emails, proposals, quotations | Find matching deal page in `~/brain/deals/` or `~/brain/projects/active_projects/`. If found, add timeline entry. If not found, flag as `brain_missing`. |
| **Projects** — project names, milestones, deliverables | Match against `~/brain/projects/active_projects/`. Add timeline or notes. |
| **HR / Hiring** — candidates, interviews, offers | Match against `~/brain/hiring/`. Link to candidate profiles. |
| **Finance** — invoices, POs, payment requests | Match against finance-related pages. Flag amount and urgency. |
| **Internal Ops** — needs CH Lim attention | Highlight in summary report. |

Use `mcp_gbrain_query` to find matching pages, not grep. The brain graph is the source of truth.

## Phase 3: BRIDGE

For each item:
1. **Extract entities** — people (email addresses, names), companies, projects mentioned
2. **Find brain pages** — use `mcp_gbrain_resolve_slugs` or `mcp_gbrain_search` to find matching person/company/project pages
3. **Create links** — use `mcp_gbrain_add_link`:
   - Person → Deal: `link_type="contact_for"`
   - Person → Company: `link_type="works_at"`
   - Meeting → Person: `link_type="attended"`
   - Calendar Event → Person: `link_type="meeting_with"`
   - Calendar Event → Company: `link_type="meeting_about"`
   - Email → Deal: `link_type="emailed_about"`
4. **Add timeline entries** — use `mcp_gbrain_add_timeline_entry` on deal/project pages for significant activity
5. **Detect risks** — run `python3 ~/.hermes/scripts/sync-deal-activity.py` which handles:
   - Stalled deals (no activity 7+ days)
   - Cold deals (qualified but silent 14+ days)
   - Overdue projects (past target date)

## Phase 4: ENRICH

Load the `profile-enrichment` skill. For each person matched:
1. Check if their brain profile is complete (company, role, contact info)
2. If incomplete, run enrichment (web search for person + company)
3. Update the person page with enriched data
4. Ensure backlinks from company → person exist

## Phase 5: VALIDATE

1. **Compliance** — for EVERY brain page modified, run:
   ```bash
   python3 ~/.hermes/skills/gbrain/brain-compliance/scripts/validate-brain-page.py <path>
   ```
   Fix ALL violations before completing.

2. **Orphan detection** — flag any entity mentioned but not found in brain:
   - Use `mcp_gbrain_resolve_slugs` to check if pages exist
   - Report missing as `brain_missing: <name>` in summary

3. **Link coverage** — use `mcp_gbrain_get_backlinks` on new pages to verify link graph is healthy

## Delivery

Every run must produce a **structured summary**:

```
📊 <SOURCE> PIPELINE — <DATE> <TIME>

📥 Collected: X items from Y accounts/calendars

🔗 Routed:
  • Sales/CRM: N deals updated
  • Projects: N project pages updated  
  • HR: N candidate signals
  • Finance: N items flagged

🧠 Brain Health:
  • X links created
  • Y pages validated (Z violations fixed)
  • Orphans flagged: <list or "none">

⚠️ Risks:
  • <any stalled/cold/overdue risks detected>
  • Items needing attention: <list>
```

## Pitfalls

- **Never skip a phase** — COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE every time
- **Always use brain tools** — `mcp_gbrain_*` not grep/ls
- **Don't auto-create pages for missing entities** — just flag as `brain_missing`
- **Run compliance validator on EVERY modified page** — not just "spot check"
- **sync-deal-activity.py is the bridge for deals/projects** — use it, don't rewrite it
- **profile-enrichment skill handles enrichment** — load it, don't inline the process
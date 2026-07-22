---
name: email-brain-classifier
description: >-
  Classify brain email pages into categories (project, deal, support, hr, other),
  detect risk/negative sentiment, and route to appropriate profiles. Designed as
  a post-collection processor for the Gmail→gbrain pipeline.
version: 1.0.0
tags: [gbrain, email, classification, routing, risk, sentiment]
---

# Email Brain Classifier & Router

After email collection imports pages into gbrain (type=email), this skill classifies each unprocessed email and routes it to the right destination.

## Classification Taxonomy

| Category | Signal Keywords | Brain Destination | Profile |
|----------|----------------|-------------------|---------|
| **project** | PO#, site visit, installation, UAT, milestone, deployment, hardware delivery, server, configuration, kickoff, go-live, snag list, defect, warranty claim, support ticket #, TS- | `projects/active_projects/<project>/` or `projects/projects/<project>/` | project-manager |
| **deal** | quotation, proposal, pricing, demo request, RFP, RFQ, contract, MOU, NDA, purchase order, invoice, payment terms, closing date, bid, tender, renewal, upsell, POC, proof of concept | `deals/<deal-slug>/` → type: deal | crm-manager |
| **support** | support ticket, issue, problem, not working, broken, down, error, bug, help, urgent fix | `projects/support_tickets/tickets/` | project-manager |
| **hr** | interview, CV, resume, job application, recruitment, candidate, offer letter, onboarding | `hr/` | hr-manager |
| **other** | newsletter, spam, marketing, personal, subscription, notification | No routing — tag as `classified` only | — |

## Risk & Sentiment Detection

Before routing, scan EVERY email for risk signals:

### HIGH RISK — alert #management IMMEDIATELY
- **Deadline missed**: "overdue", "past deadline", "delayed", "behind schedule"
- **Customer escalation**: "escalation", "CEO complaint", "not happy", "disappointed", "urgent attention"
- **Financial threat**: "cancellation", "termination notice", "refund demand", "legal action", "lawyer"
- **System down**: "server down", "system offline", "outage", "data loss", "breach", "hacked"
- **Payment dispute**: "unpaid invoice", "payment overdue > 30 days", "demand letter"
- **Negative sentiment**: angry tone, ALL CAPS frustration, threatening language

### MEDIUM RISK — log to risk register
- **Scope creep**: "additional requirement", "out of scope", "change request without PO"
- **Resource strain**: "short staffed", "no available engineer", "overbooked"
- **Vendor delay**: "supplier delayed", "parts not arrived", "customs hold"
- **Budget concern**: "over budget", "cost overrun", "need approval for additional"

### Slack Alert Format

For HIGH RISK → send immediately to `slack:G032460V7`:

```
🚨 HIGH RISK ALERT — {category} | {email_subject}

From: {from} | To: {to} | Date: {date}

**Risk Signal:** {detected_signal}
**Summary:** {one-line summary of the risk}

Brain: `{email_slug}`
```

## Processing Workflow

### Step 1 — Find Unprocessed Emails

Query brain for email pages that are NOT tagged `classified`:
```
mcp_gbrain_list_pages(type="email", sort="updated_desc", limit=20)
```
Filter to pages without `classified` tag (check `tags` field).

### Step 2 — Classify Each Email

For each unprocessed email:
1. Read full page content via `mcp_gbrain_get_page(slug)`
2. Analyze subject + body against classification taxonomy
3. Run risk/sentiment scan

### Step 3 — Route by Category

#### PROJECT emails:
1. **Resolve project**: Search brain for matching project by customer name, project name, or keywords
   - Check `projects/active_projects/` and `projects/projects/` 
   - Use `mcp_gbrain_search` with customer + project keywords
2. **Create/update project page** with email summary
3. **Add timeline entry**: `mcp_gbrain_add_timeline_entry(slug, date, summary, detail, source)`
4. **Tag email**: `mcp_gbrain_add_tag(slug, "classified")` + `mcp_gbrain_add_tag(slug, "project")`
5. **Cross-link**: `mcp_gbrain_add_link` from project page to email page
6. If risk detected → follow Risk Response below

#### DEAL emails:
1. **Resolve deal**: Search brain for matching deal by company name, deal name
   - Search for `type: concept` pages with deal indicators (Stage, Amount, Deal ID)
   - Use `mcp_gbrain_search` with company name + "deal" or "quotation"
2. **If deal page doesn't exist**: Create one under `deals/<company-slug>/` with:
   ```yaml
   ---
   title: "{Company} — {Deal Summary}"
   type: deal
   stage: "{inferred stage: Prospecting|Qualified|Quote|Negotiation|Closed Won|Closed Lost}"
   tags: [deal, crm]
   ---
   ```
3. **Add timeline entry** with email context
4. **Add notes section** with key details extracted from email
5. **Tag email**: `classified` + `deal`
6. **Cross-link**: deal page ↔ email page
7. If risk detected (e.g., deal at risk, lost deal, angry prospect) → alert

#### SUPPORT emails:
1. Match to existing support ticket if TS- number found
2. Add timeline entry to ticket
3. Tag email: `classified` + `support`

#### HR emails:
1. Create/update HR-related page
2. Tag email: `classified` + `hr`

#### OTHER emails:
1. Tag email: `classified` only
2. No routing

### Step 4 — Risk Response

- **HIGH**: Send Slack alert FIRST (before routing), then process normally
- **MEDIUM**: Log to `projects/active_projects/_risk_register.md` or `deals/_risk_register.md`
- **LOW**: Note in timeline entry only

### Step 5 — Summary Report

After processing batch, report:
- Total emails processed
- Breakdown: project=X, deal=Y, support=Z, hr=W, other=V
- Risk alerts sent: N
- New pages created: M

## Pitfalls

- ❌ Not checking if email is already classified (re-processing)
- ❌ Creating duplicate deal/project pages — always search first
- ❌ Sending Slack alert for every email — only HIGH risk
- ❌ Missing cross-links — orphaned content is invisible
- ❌ Skipping the risk scan — the most valuable feature is early warning
- ❌ Classifying based on subject alone — read the body too

## Entity Resolution Helpers

When resolving project names from email content, check these patterns:
- "PO #" → likely a project or deal email
- "SR_S" prefix → Samsung support ticket
- "TS-" prefix →  support ticket
- Company name in From/To → likely deal or project
- "demo", "POC", "trial" → deal (prospecting stage)
- "installation", "site visit", "UAT" → project (execution stage)

## Brain Path Conventions

| Category | Brain Path | Page Type |
|----------|-----------|-----------|
| Active project | `projects/active_projects/<id>_<name>/` | project |
| Legacy project | `projects/projects/<id>/` | project |
| Support ticket | `projects/support_tickets/tickets/ts-YYYY-NNN` | project |
| Deal | `deals/<company-slug>/` | deal |
| Email archive | `data/email/email-*` (unchanged) | email |
| Risk register | `projects/active_projects/_risk_register.md` | note |

## gbrain CLI Fallbacks (for subagent / terminal-only contexts)

When MCP tools are unavailable (delegate_task subagents, terminal-only crons), use these gbrain CLI equivalents:

| MCP Tool | gbrain CLI Equivalent |
|----------|----------------------|
| `mcp_gbrain_query(...)` | `gbrain query "..."` or `gbrain search "..."` |
| `mcp_gbrain_get_page(slug)` | `gbrain get <slug>` |
| `mcp_gbrain_put_page(slug, content)` | `echo "<content>" \| gbrain put <slug>` or write to `~/brain/<path>.md` |
| `mcp_gbrain_add_tag(slug, tag)` | `gbrain tag <slug> <tag>` |
| `mcp_gbrain_add_timeline_entry(slug, date, summary)` | `gbrain timeline-add <slug> <date> "<summary>"` |
| `mcp_gbrain_add_link(from, to)` | `gbrain link <from> <to>` |
| `mcp_gbrain_list_pages(type=..., tag=...)` | `gbrain list --type email -n 50` |
| `mcp_gbrain_search(query)` | `gbrain search "<query>"` |
| `mcp_gbrain_get_links(slug)` | `gbrain backlinks <slug>` |

**Key pitfall:** `gbrain put` requires full markdown content via stdin or direct file write. For creating new pages,
prefer writing to `~/brain/<category>/<slug>.md` directly, then `gbrain sync` to index.

**Anti-pattern:** When in a subagent context, do NOT try to call mcp_gbrain_* tools — they will fail silently.
Use gbrain CLI instead. Wrap commands with `timeout=30` to prevent hangs.
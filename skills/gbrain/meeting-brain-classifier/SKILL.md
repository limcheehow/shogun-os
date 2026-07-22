---
name: meeting-brain-classifier
description: >-
  Classify brain meeting pages into team categories (sales, marketing, project, hr, management),
  extract action items and decisions, route to project/deal pages with timeline entries,
  and detect risk signals. Post-collection processor for the Drive→Meeting→gbrain pipeline.
version: 1.0.0
tags: [gbrain, meeting, classification, routing, risk, action-items]
---

# Meeting Brain Classifier & Router

After the meeting collection script imports meeting notes into gbrain (type=meeting), this skill classifies each unprocessed meeting and routes it.

## Classification Taxonomy

| Team | Signal Keywords | Brain Path | Primary Profile |
|------|----------------|-----------|-----------------|
| **sales** | demo, proposal, quotation, pricing, POC, deal, prospect, renewal, pipeline, close date, commission | `meetings/sales/` | crm-manager |
| **marketing** | campaign, social media, SEO, content, branding, website, lead gen, event, booth, exhibition | `meetings/marketing/` | marketing-manager |
| **project** | UAT, deployment, hardware, installation, server, configuration, milestone, site visit, snag, defect, sprint, backlog, go-live | `meetings/projects/` | project-manager |
| **hr** | leave, salary, hiring, interview, performance, appraisal, training, onboarding, policy, compliance, ISO | `meetings/hr/` | hr-manager |
| **management** | strategy, roadmap, budget review, board, quarterly, OKR, KPI, org structure, partnership, M&A | `meetings/management/` | default |
| **other** | doesn't clearly fit above categories | `meetings/other/` | — |

## Rollup Pattern

For each team-relevant meeting, update THREE things:
1. **Meeting page** — tag + classify + move to correct path
2. **Project/Deal page** — add timeline entry + notes
3. **People pages** — cross-link attendees

## Step 1 — Find Unprocessed Meetings

Query brain for meeting pages NOT tagged `classified`:
```
mcp_gbrain_list_pages(type="meeting", sort="updated_desc", limit=15)
```
Filter to pages without `classified` tag.

## Step 2 — Classify Each Meeting

For each unprocessed meeting:
1. Read full page content via `mcp_gbrain_get_page(slug)`
2. Analyze title + attendees + content against taxonomy
3. Parse Gemini note structure: Summary, Decisions, Next steps, Details
4. Run risk/sentiment scan

### Attendee Resolution

Gemini notes list attendees in the header. Extract each name:
- Match against brain people pages: `mcp_gbrain_search(name)`
- Cross-link meeting page to each matched person page
- Use attendees to help classify (e.g., kunna+liyana = sales, syazwan+fitri = project)

## Step 3 — Route by Team

### SALES meetings:
1. **Resolve deal**: Search brain for matching deal by company name in title/content
   - `mcp_gbrain_search(company_name + "deal" OR "quotation")`
2. **If deal found**: Add timeline entry with meeting date, summary, key decisions
3. **If no deal found but prospect mentioned**: Create deal stub page under `deals/`
4. **Tag meeting**: `classified` + `sales`
5. **Cross-link**: meeting ↔ deal page ↔ attendee pages
6. **Extract action items** from "Next steps" → add as tasks on deal page

### PROJECT meetings:
1. **Resolve project**: Search brain by project name/customer in title
   - Check `projects/active_projects/` and `projects/projects/`
2. **Add timeline entry**: Meeting date + summary + decisions
3. **Add notes**: Key technical decisions, blockers mentioned
4. **Tag meeting**: `classified` + `project`
5. **Cross-link**: meeting ↔ project page ↔ attendee pages
6. **Extract action items** from "Next steps" → add as tasks on project page
7. **Risk scan**: Technical blockers, deadline pressure, resource gaps

### MARKETING meetings:
1. Tag: `classified` + `marketing`
2. Cross-link attendees
3. No project/deal routing unless campaign references specific client

### HR meetings:
1. Tag: `classified` + `hr`
2. Cross-link attendees
3. If compliance/ISO related → link to ISMS pages

### MANAGEMENT meetings:
1. Tag: `classified` + `management`
2. Cross-link attendees
3. Extract strategic action items

## Step 4 — Action Item Extraction

Gemini notes have a "Next steps" section with:
```
* [Person] Action: description
```

For each action item:
- **Sales meeting**: Add as task on the deal page
- **Project meeting**: Add as task on the project page with assignee
- **Management meeting**: Add to management tracking page

Task format on project/deal page:
```markdown
- [ ] **Action** — @assignee (from meeting YYYY-MM-DD)
```

## Step 5 — Risk Detection

Same rules as email classifier:

### HIGH RISK — alert #management (slack:G032460V7):
- Technical blocker with no owner
- Deadline pressure ("urgent", "ASAP", "behind schedule")
- Customer dissatisfaction mentioned
- Resource gaps blocking delivery
- Budget issues

### Slack Alert Format:
```
🚨 HIGH RISK — meeting | {meeting_title}

Attendees: {names} | Date: {date}

**Risk Signal:** {detected_signal}
**Summary:** {one-line summary}

Brain: `{meeting_slug}`
```

## Step 6 — Tag & Report

After processing all meetings:
- Tag each as `classified` + team tag
- Report: X meetings processed, breakdown by team, N action items extracted, M risk alerts sent

## Pitfalls

- ❌ Missing action item extraction — Gemini notes already have structured "Next steps", use them
- ❌ Not cross-linking attendees — people pages are valuable for relationship tracking
- ❌ Duplicate deals/projects — always search brain before creating
- ❌ Classifying by title only — check attendees and content too
- ❌ Skipping the risk scan on project meetings

## Team ↔ Attendee Mapping

| Name | Email | Team | Projects/Deals |
|------|-------|------|---------------|
| Admin | cheehow@example.com | Management | All |
| Kunna | kunna@example.com | Sales | Deals |
| Liyana | liyana@example.com | Sales | Deals |
| Anwar | anwar@example.com | Sales | Deals |
| Sarah | sarah@example.com | Marketing | — |
| Syazwan | syazwan@example.com | Project | Active projects |
| Ashraf | ashraf@example.com | Project | Active projects |
| Fitri | fitri@example.com | Project | Active projects |
| Iskandar | iskandar@example.com | Project | Active projects |
| Aidiel | aidiel@example.com | Support | Support tickets |
| Paul Rydrick | paulrydrick@example.com | Project | Active projects |
| Hana | hana@example.com | HR | HR |
| Hairul | hairul@example.com | Admin/Finance | Procurement |
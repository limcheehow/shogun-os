---
name: gbrain-enrich
description: "Tiered enrichment for person, company, and project pages — add facts, timeline entries, cross-links, and data validation."
version: 1.0.0
author: user
tags: [gbrain, enrich, profile, augment]
---
# gbrain Enrich

Tiered enrichment pipeline for entity pages. Use when a page exists but is thin, or when you have new information to add.

## Enrichment Tiers

### Tier 1 — Quick Enrichment (5 min)
- Add missing tags via `mcp_gbrain_add_tag`
- Link to related entities via `mcp_gbrain_add_link`
- Add timeline entries for dated events via `mcp_gbrain_add_timeline_entry`
- Update outdated sections

### Tier 2 — Structured Enrichment (15 min)
- Add structured sections: Bio, Role, Contact, Background for people pages
- Add Product, Market, Team, Financial for company pages
- Add Timeline, Status, Decisions for project pages
- Extract and add facts via `mcp_gbrain_extract_facts`
- Cross-reference with related pages

### Tier 3 — Deep Enrichment (30 min+)
- Research gaps identified by `mcp_gbrain_think`
- Add fact tables with typed metrics (MRR, team_size, etc.)
- Write synthesis sections that summarize compound knowledge
- Flag contradictions found via `mcp_gbrain_find_contradictions`
- Enrich with data from external sources (web research, APIs)

## Standard Enrich Workflow

1. **Read** — `mcp_gbrain_get_page(slug)` to see current state
2. **Assess** — what's missing? Tags? Links? Timeline? Structured data?
3. **Fill** — add what's missing with the appropriate tool
4. **Verify** — re-read the page to confirm quality
5. **Back-link** — ensure the enriched page has outbound links and receives back-links

## Entity Template Sections

### Person
```yaml
---
tags: [person, staff, engineering]
---
## Bio
Brief description of who they are.

## Role
Current role, team, reporting structure.

## Contact
Email, Slack ID, phone (per privacy rules).

## Background
Career history, education, key skills.
```

### Company
```yaml
---
tags: [company, customer, vendor]
---
## Overview
What they do, size, location.

## Relationship
How we work with them, key contacts.

## Product/Service
What they offer.

## Timeline
Key events in our relationship.
```

### Project
```yaml
---
tags: [project, internal]
---
## Status
Current state, next milestone.

## Team
Who's involved.

## Decisions
Key decisions made.

## Timeline
Dated milestones.
```

## Pitfalls

- ❌ Overwriting existing good content — enrich, don't replace
- ❌ Adding facts without dates (timeline entries need dates)
- ❌ Skipping back-links — a linked page is 10x more discoverable
- ❌ Contradictory data without flagging the conflict
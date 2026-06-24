---
name: profile-enrichment
description: "Enrich company and contact profiles via web research, then persist to gbrain. Used by CRM (Kizuna), Marketing (Haiku), and HR (Jinzai). Uses gbrain put_page for canonical writes."
version: 1.0.0
tags: [shared, enrichment, people, companies, research, crm, marketing, hr]
triggers:
  - "enrich profile"
  - "research company"
  - "research person"
  - "enrich contact"
  - "company intel"
  - "competitive research"
  - "lead enrichment"
---

# Profile Enrichment — gbrain-Native

> **Canonical path:** `mcp_gbrain_put_page` into the profile's source
> **Used by:** CRM (crm/), Marketing (marketing/), HR (shared/staff/)
> **Research via:** web_search, company websites, SEC filings, news

## Workflow

### 1. Company Enrichment

When a new company is encountered (deal, prospect, partner, vendor):

```python
# 1. Check if company already exists
result = mcp_gbrain_search(
    query=f"type:company name:\"{company_name}\"",
    source="crm"  # or marketing, procurement depending on profile
)

# 2. Research company via web
web_search(query=f"{company_name} company overview headquarters employees")
web_search(query=f"{company_name} funding investors")

# 3. Write enriched profile to gbrain
mcp_gbrain_put_page(
    slug=f"companies/{slug}",
    source="crm",
    content=f"""---
type: company
name: \"{name}\"
industry: \"{industry}\"
website: \"{website}\"
headquarters: \"{hq}\"
employees: {employees}
founded: {year}
tags: [company, {industry_tag}]
---

# {name}

## Overview
{summary}

## Key Facts
- **Industry:** {industry}
- **Employees:** {employees}
- **Headquarters:** {hq}
- **Website:** [{website}]({website})

## Competitive Landscape
{competitive_notes}

## Notes
{enrichment_notes}
"""
)
```

### 2. Person/Contact Enrichment

When a new person is encountered:

```python
# 1. Check existing
mcp_gbrain_search(query=f"name:\"{person_name}\"", source="crm")  # or shared/staff/ for HR

# 2. Research
web_search(query=f"{person_name} {company_name} profile")

# 3. Write to gbrain
mcp_gbrain_put_page(
    slug=f"contacts/{slug}",
    source="crm",
    content=f"""---
type: person
name: \"{name}\"
company: \"{company}\"
role: \"{role}\"
email: \"{email}\"
linkedin: \"{linkedin}\"
tags: [contact, {company_tag}]
---

# {name}

**Role:** {role}
**Company:** [[{company_slug}]]
**Email:** {email}
**LinkedIn:** {linkedin}

## Background
{research_notes}

## Relationship
{interaction_history}
"""
)
```

## Source Routing

| Profile | Write Source | Read Sources |
|---|---|---|
| **CRM (Kizuna)** | `crm/` (companies, contacts, deals) | `crm/` + `shared/` |
| **Marketing (Haiku)** | `marketing/` (campaigns, leads) | `marketing/` + `crm/` + `shared/` |
| **HR (Jinzai)** | `shared/staff/` (employees) | `shared/` |

## When to Enrich

- After every client meeting — enrich the company + contacts
- When a new deal is created — research the prospect
- Before a proposal — competitive intel on the prospect
- After a conference/event — batch enrich leads
- Weekly — check for stale profiles (last updated > 90 days)

## Output

```
✅ Enriched: {company_name}
- Added industry: {industry}
- Found {n} key contacts
- Added competitive notes
- Saved to crm/companies/{slug}
```
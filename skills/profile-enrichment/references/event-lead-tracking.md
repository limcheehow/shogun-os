# Event Lead Tracking — NRF Example

This reference documents the NRF lead tracking session as a concrete example of the Event-Sourced Lead Tracking pattern.

## Context

- **Event:** NRF (National Retail Federation) — retail tech trade show
- **Tracking period:** June 2–5, 2026 (3 days after the event)
- **Lead #1:** JARTON Group (Thailand) — smart property solutions, smart city, shopping malls
- **Contact:** T-Tutt Jungkankul — CEO / CTO / CIO

## Files Created

| File | Content | Notes |
|------|---------|-------|
| `~/brain/nrf-leads-tracker.md` | Running leads log for NRF | One tracker per event |
| `~/brain/companies/jarton-group.md` | Full company profile | Tagged source=event, tag=NRF |
| `~/brain/contacts/t-tutt-jungkankul.md` | Contact profile | Tagged source=event, tag=NRF |

## Tracker Template

```markdown
# {Event Name} Leads Tracker

**Event:** NRF (National Retail Federation)
**Source:** event
**Tag:** NRF
**Tracking period:** June 2–5, 2026

## Leads

| # | Company | Contact | Profile Saved | Notes |
|---|---------|---------|---------------|-------|
| 1 | JARTON Group | T-Tutt Jungkankul (CEO) | brain/companies/jarton-group.md | Smart city, shopping malls, smart buildings. |
```

### Source/Tag Frontmatter

In each company or person file, add as plain Markdown (not YAML frontmatter — brain files use ### headers, not YAML):

```markdown
**Source:** event
**Tag:** {EVENT}
**Lead owner:** user (Your Company)
**First contact:** Name (Title)
```

## Workflow

1. User drops a lead — can come via:
   a. **Name + company mention** — "who is X from Y?" or "research Y company"
   b. **Business card image** — see Business Card Scanning section below
   c. **Website URL** — "who's example.com?"
   d. **Directory app screenshot** — see `references/directory-screenshot-batch-processing.md` for batch extraction workflow (3-5 contacts per screenshot)
2. Research the company and contact (web search → LinkedIn → Apollo)
3. Save company profile to `~/brain/companies/` with source/tag frontmatter
4. Save contact profile to `~/brain/contacts/` with source/tag frontmatter
5. Log to the event's tracker file
6. **If user asks for follow-up** — set a cron job reminder (see Cron Follow-Up section below)
7. **If user asks for intro/booth invite email** — use the `your-company-sales-intro-email` skill (Variant B for directory-sourced contacts, Variant C if met in person)
8. For duration window: this applies automatically; after it expires, tags remain as metadata

## Business Card Scanning Workflow

When the user sends a **photo of a physical business card** (common at trade shows):

1. **vision_analyze** the image — extract: person name, job title, company name, phone, email, website
2. Note any discrepancy between what the user says and what the card shows (e.g. user says "Histone", card says "HiStone") — correct the user gently
3. **Research the company** via web_search — same as any lead (website → news → funding → product lines)
4. **Research the contact** — LinkedIn, news mentions, conference talks
5. **Create profiles** with source/tag/lead_owner frontmatter
6. **Log to event tracker**
7. **Offer to set follow-up reminder** — use cronjob for next-morning prompt

### Directory Convention

- Company profiles → `~/brain/companies/{slug}.md`
- Contact profiles → `~/brain/contacts/{slug}.md`
- Event tracker → `~/brain/{event-name}-leads-tracker.md`

### Source/Tag Frontmatter

```markdown
**Source:** event
**Tag:** {EVENT}
**Lead owner:** user (Your Company)
**First contact:** Name (Title)
```

## Cron Follow-Up Reminder

After saving a lead, if the user says "remind me to follow up" or implies a deadline:

1. Create a one-shot cron job with `cronjob(action='create')`:
   - `name`: "Follow-up: {Name} ({Company}) - {Event} Lead"
   - `prompt`: Self-contained reminder with contact details, company context, and a clear call to action
   - `schedule`: ISO timestamp for the requested time (e.g. `2026-06-03T09:00:00` for tomorrow morning)
   - `deliver`: `'origin'` (auto-detects current chat)

2. The cron job fires once, delivers the reminder as a fresh message to this chat, then expires.

### Prompt Template for Cron Reminder

```
Remind user to follow up with {Name} from {Company} ({website}).
He's the {Title} for {Company}, a {brief 1-sentence company description}.
He proactively reached out / was identified at {event}.
Contact: {email}, {phone}
{Company} makes {product} - {relevance to Your Company}.
Deliver this reminder with a clear call to action.
```

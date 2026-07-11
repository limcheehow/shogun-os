# Business Card Ingestion — Lightweight Contact Capture

When the user sends **photo(s) of business cards** with a simple instruction like "add to my brain" or "save these contacts", use this lightweight workflow. It's faster than the full enrichment pipeline — just archive the image, create contact files from the card data, deduplicate, and crosslink into a meeting note.

This is for **surface-level capture** (what's on the card). Use the main `profile-enrichment` SKILL.md for deep enrichment (web search, LinkedIn, Apollo).

## Workflow

### 1. Archive the Image

Always copy the image from the cache to `~/brain/attachments/` first:

```bash
cp /path/from/image_cache/img_xxx.jpg ~/brain/attachments/YYYY-MM-DD-description.jpg
```

Use a concise description: `2026-06-04-business-cards-company1-company2-company3.jpg`

### 2. Deduplicate Against Existing Brain

Before creating any contact files, check if any of the people already exist:

```bash
# Search by name patterns
ls ~/brain/contacts/ | grep -i '<name-pattern>'

# Also check persons/ directory for older entries
ls ~/brain/persons/ | grep -i '<name-pattern>'
search_files(path="~/brain", pattern="<email-domain>")
```

If a contact already exists:
- **Do NOT create a duplicate file**
- Add a timeline note to the existing file: `Card received again on YYYY-MM-DD (another event)`
- Note the repeat in the meeting note

### 3. Create Contact Files

Each new contact gets a file in `~/brain/contacts/<firstname-lastname-company>.md`.

**Contact file template:**

```markdown
# First Last

**Title:** Exact Title from Card
**Company:** Full Company Name
**Email:** email@company.com
**Mobile:** +XX XXXX XXXX
**Website:** www.company.com
**Source:** Business card (in-person meeting)

## Address
Street address
City, State/Country

## Notes
- Company context / what they do
- Potential relevance to Your Company
- Met at event (same batch as other cards collected same date)
```

**Key rules:**
- Use the **exact name** as it appears on the card (including honorifics like Prof, Dr, etc.)
- Include alternative contact channels (Tel, GL, DID, Fax) if present
- List **all company entities** from the card (e.g., Dabton had 6 subsidiaries listed)
- List **all brand/product names** from the card (e.g., SKYAPP, 3Dab, AEVIS TRACK)
- Include **affiliations/associations** if on card (e.g., SAMENTA, FIABCI, PPK, BNI)
- Note **potential relevance** to Your Company/ITMAX in the Notes section — this helps CH prioritize follow-ups
- **Reference the business card image** in Notes with a path link path (e.g. `[[attachments/2026-06-04-business-cards-company1-company2-company3.jpg]]`)

### 4. Create / Update a Meeting Note

Create a single `~/brain/meetings/YYYY-MM-DD-business-cards-collected.md` file for all cards collected on that date. Group by card set (one image = one set):

```markdown
# Business Cards Collected — YYYY-MM-DD

## Card Set 1
- **Name** — Role, Company [[contacts/name-company]]
- **Name** — Role, Company [[contacts/name-company]]
- Image: [[attachments/YYYY-MM-DD-desc.jpg]]

## Card Set 2
...
```

If the meeting note already exists (from a previous card set in the same session), **append** to it rather than creating a new file.

### 5. Summarize for the User

End with a clean summary table:

| Name | Company | Status |
|---|---|---|
| Person A | Company A | ✅ New contact saved |
| Person B | Company B | ⚠️ Already in brain (met Mon X Date, updated with 2nd card note) |
| Person C | Company C | ✅ New contact saved |

Add a brief note on any stand-out contacts (potential partners, repeat encounters, notable affiliations).

### 6. (Optional) Google Contacts Sync

If the user has a Google Contacts integration (OAuth token with `contacts` scope), and the contact has a **phone number**, also create a Google Contact so it syncs to their phone:

```bash
GAPI="python3 $HERMES_HOME/skills/productivity/google-workspace/scripts/google_api.py"

# Pre-check: does this email already exist in Google?
$GAPI contacts list --max 200 | python3 -c '
import sys, json
data = json.load(sys.stdin)
all_emails = set()
for c in data:
    for e in c.get("emails", []):
        all_emails.add(e.lower())
targets = ["email1@co.com", "email2@co.com"]
missing = [t for t in targets if t.lower() not in all_emails]
print(" ".join(missing))
' | read -ra MISSING

# Create only the missing ones
for email in "${MISSING[@]}"; do
  $GAPI contacts create --given-name "First" --family-name "Last" --email "$email" ...
done
```

This is optional — only do it when the user explicitly asks to save contacts to their phone / Google Contacts. See the `save-to-google-contacts` skill for details.

## Deep Enrichment (When Requested)

If the user follows up with "enrich all the profiles above" after lightweight capture, switch to the full profile-enrichment pipeline. For 10+ contacts from a single event, use **batch parallel enrichment** via `delegate_task` for efficiency.

### Batch Enrichment via Subagents

When researching 10-15 contacts in one go, **do not research them one at a time** (that takes 15+ turns of sequential web_search). Instead:

1. **Split into groups of 3-5** and spawn parallel `delegate_task` subagents (respecting 3-concurrent limit)
2. Each subagent gets **rich context** — the person's name, role, company, email, phone, address from the card
3. Ask each subagent to research via `web` toolsets and **return structured data** for each person

**Subagent prompt template:**

```
Research these N people and their companies via web search. Find LinkedIn profiles,
bios, company backgrounds, recent news. Return structured data for each person.

Person 1: {Name} — {Role} at {Company}. Email: {email}. Phone: {phone}. Address: {address}
Person 2: ...
```

4. **Consolidate findings** — each subagent returns a comprehensive summary. Read all results, then write/update contact files with the enriched data.

**Timing:** With 3 parallel subagents and 15 contacts, research completes in ~2 minutes (vs 15+ if sequential).

### Enriched Contact File Format

When enriching business card contacts beyond lightweight capture, use this comprehensive format (more detail than the base profile-enrichment template):

```markdown
# Full Name

**Title:** Exact Title(s) from card + researched titles
**Company:** Company Name
**Email:** email@company.com
**Phone:** +XX XXXX XXXX
**Website:** www.company.com
**LinkedIn:** linkedin.com/in/username
**Source:** Business card (in-person meeting)

## Background
- Career history in bullet points (current role, previous roles, education)
- Location / based in

## Company — Name
| Attribute | Detail |
|---|---|
| Founded | Year |
| HQ | City, Country |
| Employees | Count |
| Revenue | If public |
| Key Facts | Relevant context |

## Recent News & Activity
- **Date:** News item with key detail
- **Date:** Another item

## Notes
- Relevance to Your Company/ITMAX
- Follow-up priority
```

Key additions over the base template:
- **Company info table** — quick reference for CH without having to open a separate company file
- **Recent News section** — dated bullet points of relevant press, events, partnerships
- **LinkedIn** — always include when found (personal, not just company page)
- **Enriched title** — reflect additional researched titles (e.g. also-CEO-of-subsidiary) on top of the card's printed title

### Dedup During Batch Enrichment

For each batch, check sites BEFORE writing:

```bash
# Check both contacts/ and persons/ directories
ls ~/brain/contacts/ | grep -i '<name>'
ls ~/brain/persons/ | grep -i '<name>'
```

If a contact already exists from a prior event:
- **Patch** the existing file with new background + company + timeline entries (don't create a new file)
- Note the repeat sighting in the meeting note
- Update their LinkedIn if missing from the earlier entry

### Pitfalls (Batch Enrichment)

- ❌ **Don't research all 15 sequentially** — use subagents for parallel work
- ❌ **Don't create duplicate files** — even during enrichment, check both `contacts/` and `persons/` before writing
- ❌ **Don't skip web search in favor of LinkedIn only** — company news and context come from web search, LinkedIn only has career history
- ✅ **Do include news/event dates** — CH uses these to assess relevance and recency
- ✅ **Do include the company table** — it saves CH from opening the company file separately
- ✅ **Do cross-reference same-city/same-event contacts** — WINTEC + HiStone are both Qingdao POS companies — flag the connection

## Pitfalls (Lightweight Capture)

- ❌ **Don't deep enrich unless asked** — this is lightweight capture. Skip web search, LinkedIn, Apollo unless the user asks for it.
- ❌ **Don't create duplicates** — always dedup against both `contacts/` and `persons/` directories before creating files.
- ❌ **Don't overwrite existing files** — read first, append timeline entries.
- ✅ **Do check `persons/` directory too** — older contacts may be in `~/brain/persons/` rather than `~/brain/contacts/`.
- ✅ **Do note potential Your Company/ITMAX relevance** — CH values knowing who's worth following up.
- ✅ **Do include the image path** in each contact file's Notes so the card image is findable.
- ✅ **Do batch into a single meeting note per date** — separate notes for each card set creates clutter.

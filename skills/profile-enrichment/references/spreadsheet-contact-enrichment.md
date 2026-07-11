# Spreadsheet Contact Enrichment — Conference / Event / Trade Show Leads

When CH provides a spreadsheet (xlsx/csv) of conference or event contacts and asks you to fill in missing email addresses and/or LinkedIn profiles.

**This is NOT the same as profile-enrichment into brain files.** The user wants the spreadsheet back with data filled in, not individual `~/brain/persons/*.md` files. The research pipeline is shared; the output format is different.

## When to use

- CH uploads a contact spreadsheet from NRF Big Show, Retail Asia Expo, or similar events
- The spreadsheet has columns like: Company, Contact Name, Title, Email (mostly blank), LinkedIn URL (mostly blank)
- CH says: "fill in the missing contact details" or "find emails/LinkedIn for outreach"

## Workflow

### Step 1: Read the spreadsheet

```python
import pandas as pd
df = pd.read_excel(path, sheet_name=0)  # or pd.read_csv()
```

Identify columns: Company, Contact Name, Title, Email, LinkedIn URL, Priority/Region/Source.

**Categorize the gaps:**
1. **Rows WITH contact name + NO email** — best candidates, research by name+company
2. **Rows with NO contact name** — harder, need to find relevant IT leader at the company
3. **Rows with email but missing LinkedIn** — quick LinkedIn search

### Step 2: Prioritize by tier

Do High Priority contacts first, then Medium. The user will appreciate having the top targets filled even if the bottom tier remains empty.

### Step 3: Research pipeline (per contact)

**For named contacts:**
Run targeted web searches combining name + company + title:

```python
web_search("First Last Company role email")
```

Sources to try (in order):
1. **Company leadership/team pages** — most reliable for role confirmation
2. **LinkedIn** — `linkedin.com/in/firstlast` (lowercase, no hyphens)
3. **Email format discovery** — some data sites expose the email pattern for a company domain (e.g., `first.last@company.com`)
4. **News/press releases** — often contain contact emails for exec quotes

For email discovery, use:
- Company domain pattern: most companies use `first.last@company.com` or `firstlast@company.com`
- Probe via web search: `"First Last" "company.com" email`
- LinkedIn engagement posts sometimes reveal email in engagement metadata

**For unnamed contacts (company without named person):**
- Search for the company's CIO, CTO, CDO, Head of IT, or relevant technology leader
- Look for recent hires or announcements
- Note the company's general LinkedIn page as a fallback

### Step 4: Build the update dictionary

```python
updates = {
    "Company Name": ("email@company.com", "https://linkedin.com/in/username"),
}
```

### Step 5: Write back to the spreadsheet

Use `openpyxl` to modify cells in-place. Save as a new file with `-ENRICHED` suffix to preserve the original:

```python
import openpyxl
wb = openpyxl.load_workbook(src_path)
ws = wb.active
ws.cell(row=N, column=EMAIL_COL).value = "email@company.com"
wb.save(dst_path)
```

**Important:** Save to a different path (e.g., `*-ENRICHED.xlsx`), not the original uploaded file in the cache directory. Deliver the enriched copy to the user via MEDIA:.

### Step 6: Report results

When delivering, include:
- **How many rows now have emails** (e.g., "81/132 rows now have emails")
- **How many new emails found** (+42 in this session)
- **How many new LinkedIn added** (+26)
- **Which high-priority ones were filled** (top 5-10 by name)
- **What's still missing** and why (Japanese companies with fewer public emails, unnamed contacts, etc.)

## Pitfalls

- **Don't create individual brain files** unless CH explicitly asks — they want the spreadsheet back for outreach, not database enrichment
- **Some data sites gate emails behind paywalls** (RocketReach, Apollo, SignalHire, Adapt.io, Growjo). These sites show the email format is confirmed but redact the actual address behind a paywall. You can still infer the format (e.g., `m*******@aldi.com.au` → `marc.stephan@aldi.com.au` using `first.last@company.com` pattern). Don't pay; infer from the format hint.
- **Wrong LinkedIn URLs** — the spreadsheet may contain copy-paste errors (e.g., Vincent Ferreux's LinkedIn URL was accidentally used for Karim Hamdoune's row at LVMH). Catch these by verifying the LinkedIn name matches the contact name.
- **Asian names may not follow first.last patterns** — Chinese, Japanese, and Korean names often don't have simple email patterns. Accept lower hit rates for these.
- **Japanese company contacts** — Daiso, FamilyMart, Muji, Nitori, Lawson, Kinokuniya have very low email discoverability in Western sources. Note this in the report rather than spending excessive time.
- **Medium priority with no contact name** — these are the hardest to research. If the Source says "Existing (enriched)", check the brain for existing contacts first. If "NRF Profile (new)", one-sentence company-level LinkedIn is acceptable as a fallback.
- **Use openpyxl, not csv** — xlsx preserves formatting, columns, and data types. The user shared xlsx, return xlsx.
- **Verify table row anchors when extracting** — row numbers in the script can shift if the data changes. Always build a company-name -> row-number lookup dict rather than hardcoding row indices.
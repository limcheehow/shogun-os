# Directory App Screenshot — Batch Contact Extraction

When the user sends a **screenshot of an event directory app** (NRF, CES, etc.) with a search results list of contacts:

## Workflow

### Phase 1: Parse the Screenshot

1. **Read the image** using `vision_analyze` — extract every contact row: name, title, company
2. **Map the text to parsed fields:**
   - Job titles have abbreviations: DMM = Divisional Merchandising Manager, A&P = Advertising & Promotions, BD = Business Development
   - Company may be listed under parent group (e.g. "DFI" not "Guardian")
   - Same person may appear twice with slightly different titles
3. **Archive the image** to `~/brain/attachments/YYYY-MM-DD-{company}-directory-contacts.jpg`

### Phase 2: Research the Company

1. `web_search "{Company} retail stores revenue"` — store count, revenue, parent group
2. `web_extract` the company About page or Wikipedia entry for overview
3. Key fields to capture: founded year, HQ, store count/network, parent company/group, leadership/key execs, recent developments (new tech, expansion, rebranding)

### Phase 3: Research Each Contact

For each person in the screenshot:
1. `web_search "Full Name Title Company"` — look for LinkedIn bio, news mentions, company profile
2. Note: role, tenure, location, any media quotes or public speaking
3. Assign relevance to Your Company based on their role (Marketing Director → cares about traffic analytics; CRM Manager → data integration; DMM → heatmaps/merchandising)

### Phase 4: Research Email Formats — Apollo-First Approach

**CRITICAL: Always use Apollo API first to find the email pattern from verified contacts before falling back to web-scraped data.**

1. **Determine the email domain** (check company website contact page, privacy policy)
2. **Apollo-First — look up 1-2 contacts via people/match** to find verified emails:
   ```bash
   curl -s -X POST "https://api.apollo.io/api/v1/people/match" \
     -H "X-Api-Key: $APOLLO_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"domain": "company.com", "first_name": "First", "last_name": "Last"}'
   ```
   - Extract the username format from the verified email (e.g. `linda_chen@` → `first_last@`)
   - Apply that pattern to all remaining contacts from the same company domain
3. **If Apollo returns multiple patterns for the same domain** (e.g. `firstlast@` for Person A, `first@` for Person B), list both and use the most common one as primary estimate; flag remaining as "estimated"
4. **If ALL Apollo lookups return empty** for a company, fall back to web search: `web_search "{Company} email format @{domain}"` — check RocketReach, SignalHire, LeadIQ, AeroLeads
5. **Flag all emails clearly:**
   - `✅ Apollo verified` — Apollo returned it with `email_status: verified`
   - `⚠️ estimated from Apollo pattern` — applied pattern from verified contacts
   - `⚡ inferred from web data` — from RocketReach/SignalHire/LeadIQ (no Apollo data available)

**Why Apollo-first?** Web-scraped email format databases (RocketReach, SignalHire) often report generic patterns that don't match actual verified emails. For large companies with diverse email formats, Apollo's `people/match` returns the actual verified address for specific individuals, making it far more reliable. The `people/search` (bulk) endpoint is blocked on this key — use `people/match` one-by-one.

### Phase 5: Create Files

For a batch of 3-5 contacts from one company:

1. **Company profile** → `~/brain/companies/{slug}.md`
   - Store count, revenue, parent group, leadership
   - Email format research results
   - Your Company use cases by industry (from `your-company-sales-intro-email` skill's Use Case Bullets)
   - Deal pipeline table (status: "Not yet contacted")

2. **Contact profiles** → `~/brain/contacts/{slug}.md`
   - Title, company, email (with inference note)
   - Bio summary, relevance to Your Company
   - Source + tag frontmatter: `source: event, tag: NRF`

3. **Update event tracker** → `~/brain/{event-name}-leads-tracker.md`
   - Append row with lead #, company, all contacts, profile saved path, key notes
   - Keep numbering sequential from existing tracker

4. **Update activity log** → `~/brain/deals/activity-log.md`
   - One entry per batch noting company, lead #, contacts, what was created

### Phase 6: Draft the Email

Use `your-company-sales-intro-email` skill's **Variant B (Cold Intro + Booth Invite)** when the contact was found in a directory app (not met in person).

1. Address the most senior/relevant contacts (MD, Director level)
2. CC less senior contacts + liyana@your-domain.com
3. Pick 2-3 Your Company use case bullets from the skill's industry list
4. Save as Gmail Draft using multipart/alternative MIME format

**Critical: Do NOT say "It was great meeting you"** — the directory is a list of attendees, not a handshake log. Use "I hope this message finds you well" (cold intro language).

### Phase 7: Deliver Summary

Present structured output with:
- Lead # and company name in a ✅ header
- Company snapshot (stores, revenue, parent)
- Contact table (name, title, email)
- What was saved and where
- Whether draft was saved and its message ID
- Any flags (conflicting email formats, unverified data, inferred emails)

## Pitfalls

- **Same person, different title** — Anna Ng appeared twice: "Marketing Director, Guardian" and "Marketing Director, H&B, Malaysia, Brunei & Singapore" — these are the same person, don't create duplicate profiles
- **Three contacts from one screenshot** → one company profile, one email draft, multiple contact profiles — don't create duplicate company files
- **Abbreviated roles** — DMM (Divisional Merchandising Manager), A&P (Advertising & Promotions), BD (Business Development) — spell out in profiles
- **Company listed under parent** — "DFI" not "Guardian" for Joyce Lim — double-check the company attribution
- **Don't overwrite existing tracker** — append to it
- **Email format research is the most error-prone step** — allocate time for cross-referencing, and always flag uncertainty
- **Parallel company research** — research the company AND all contacts in parallel with `delegate_task` or batch web searches when processing 3+ batches in one session
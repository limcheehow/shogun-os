---
name: profile-enrichment
description: "Universal profile enrichment skill for user's brain. After any interaction (email, meeting, calendar event, social media export), enriches ~/brain/persons/ or ~/brain/friends-and-family/ with web-researched profiles, LinkedIn data, and timeline entries. Used by all brain-enrichment cron jobs. Also covers spreadsheet-based event contact enrichment (different output: fill xlsx in place, not create brain files)."
version: 2.6.0
author: user
tags: [brain, enrichment, people, companies, friends, facebook, linkedin, research, spreadsheet]
---

# Profile Enrichment — Universal Brain Enrichment Pipeline

After every interaction (email processed, meeting transcript synced, calendar event enriched, conference contacts collected), run this enrichment step BEFORE finishing. This is the canonical way to update `~/brain/persons/` and `~/brain/companies/`. EACH PERSON GETS THEIR OWN FILE — never save a single consolidated contacts list.

**Batch enrichment shortcut:** For 10+ contacts from a single event (e.g. 15 business cards received in one session), use `delegate_task` with 3 parallel subagents to research them in parallel. Each subagent researches 3-5 people via web search and returns structured data. Consolidate results and write all files in one pass. See `references/business-card-ingestion.md` → "Deep Enrichment (When Requested)" for the full workflow.

**Exception: Spreadsheet contact enrichment.** When CH provides an xlsx of event contacts (e.g., NRF Big Show) and asks to fill missing emails/LinkedIn FOR OUTREACH — do NOT create individual brain files. Fill the spreadsheet in place and return it. See `references/spreadsheet-contact-enrichment.md`.

## Triggers (always use after)

This skill fires whenever you process:
1. **Emails** — after email-classifier/email digest, before delivering results
2. **Meeting transcripts** — after meeting-agent sync, after gbrain import
3. **Calendar events** — after calendar-to-brain-sync, after attendee extraction
4. **Conference / Event contacts** — after importing an event CSV, business card scan, or speaker list. Generate individual person files for each contact rather than a single consolidated spreadsheet.
5. **Social media exports** — Facebook friends list, LinkedIn connections export, Instagram contacts. These are PERSONAL contacts, NOT business CRM. Write to `~/brain/friends-and-family/` not `~/brain/persons/`.

## Prerequisites: Chrome CDP for LinkedIn Research

This skill now uses **browser-use** with your real Windows Chrome (logged into LinkedIn) via CDP. This bypasses search engine blocks and LinkedIn authwalls.

Chrome must be running with remote debugging enabled **before** enrichment starts:

1. Run the batch file from Windows: `Desktop\\Chrome_Debug.bat` (or Chrome on port 9223 with portproxy on 9222)

2. **If the batch file fails** (profile copy too slow, Chrome doesn't relaunch), launch Chrome remotely from WSL:
```bash
# Kill existing Chrome processes first
powershell.exe -Command "Get-Process chrome | Stop-Process -Force" 2>/dev/null
sleep 2
# Launch with debug flags
powershell.exe -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9223', '--user-data-dir=C:\Users\your-company\chrome-debug-profile'" -PassThru
```
Then wait 3-5 seconds for Chrome to start before verifying. See `references/remote-chrome-launch.md`.

3. Verify connection from WSL:
```bash
GW=$(ip route show default | awk '{print $3}')
curl -s --max-time 3 "http://${GW}:9222/json/version" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Chrome {d[\"Browser\"]}')"
```

**Critical CDP troubleshooting: Connection reset by peer**

> "Connection reset by peer" on port 9222 (curl `Recv failure: Connection reset by peer`) is almost always **Chrome not running with `--remote-debugging-port` at all** — NOT a Chrome 148+ protocol incompatibility. The reset means TCP connected but Chrome's HTTP endpoint isn't there.

**Step 1: Check if Chrome is actually listening on the debug port.**
```bash
powershell.exe -Command "netstat -ano | findstr ':9223'"
```
- If **output is empty** → Chrome didn't launch with `--remote-debugging-port=9223`. Relaunch Chrome (see Remote Launch below). This is the #1 cause of "connection reset".
- If **it shows LISTENING** → the portproxy may be stale. Reset it:
  ```bash
  /mnt/c/Windows/System32/netsh.exe interface portproxy delete v4tov4 listenport=9222
  /mnt/c/Windows/System32/netsh.exe interface portproxy add v4tov4 listenport=9222 connectport=9223 connectaddress=127.0.0.1
  ```
- If **both are fine** (portproxy + Chrome listening) and you still get resets → check for a firewall rule blocking the WSL-to-Windows bridge. The firewall rule `Chrome_Debug_9222` must allow inbound on all profiles (Domain, Private, Public).

**Step 2: Remote Chrome Launch from WSL (when Chrome_Debug.bat fails)**

When running `Chrome_Debug.bat` on the Windows desktop isn't feasible (user away from PC, batch file didn't relaunch Chrome, debug profile copy took too long), launch Chrome with debug flags directly from WSL:

```bash
# Kill existing Chrome (batch script kills all to avoid port conflict)
powershell.exe -Command "Get-Process chrome | Stop-Process -Force" 2>/dev/null
sleep 3  # Wait for process cleanup

# Launch with debug flags using the existing debug profile
powershell.exe -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9223', '--user-data-dir=C:\Users\your-company\chrome-debug-profile'" -PassThru
sleep 3  # Wait for Chrome to start

# Verify
GW=$(ip route show default | awk '{print $3}')
curl -s --max-time 3 "http://${GW}:9222/json/version" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Chrome {d[\"Browser\"]}')"
```

The `-PassThru` flag is required for `Start-Process` to return the process info. Without it, the PowerShell command silently returns nothing and Chrome may not have launched.

**NOTE:** This remote launch uses the Chrome debug profile (`chrome-debug-profile`) which was copied from your real profile earlier. IF you've never run `Chrome_Debug.bat` successfully, this profile may not have your LinkedIn session. In that case, either:
- Ask CH to log into LinkedIn in the Chrome window that pops up on their desktop
- Run `Chrome_Debug.bat` once to establish the profile copy, then future remote launches will carry the session

**Step 3: Verify Chrome process + port**
```bash
powershell.exe -Command "Get-Process chrome | Where-Object { $_.Id -eq (Get-NetTCPConnection -LocalPort 9223 -ErrorAction SilentlyContinue).OwningProcess } | Select-Object Id,StartTime,@{N='CmdLine';E={(Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\" -ErrorAction SilentlyContinue).CommandLine}}" 2>/dev/null
```
This shows the exact command-line used to launch Chrome. You should see `--remote-debugging-port=9223` in the output.

**Common failures:**
- Chrome launches but port 9223 shows LISTENING only on 127.0.0.1, not 0.0.0.0 — this is correct, the portproxy handles bridging from 0.0.0.0:9222
- Chrome launches but immediately exits — check `--user-data-dir` path is valid and the profile isn't corrupted
- The user sees a Chrome window pop up on their Windows desktop — this is expected and confirms Chrome is running
- Chrome processes show no `--remote-debugging-port` flag — Chrome was launched normally (e.g. from Start Menu, pinned taskbar, or desktop shortcut), not via the debug command. Kill all Chrome and re-launch with the flag.

**Before:** The skill previously recommended `existing-tab-extraction.md` as the Chrome 148+ fallback. This was based on a misdiagnosis — the "connection reset" error was actually Chrome not running with debug flags. The correct fix is to launch Chrome properly, not to work around a phantom protocol incompatibility. The existing-tab extraction technique still works as a secondary fallback if navigation hangs, but it should not be the first response to a connection reset error.
```bash
powershell.exe -Command "netstat -ano | findstr ':9223'"
```
If output is empty, Chrome didn't launch with `--remote-debugging-port=9223` — relaunch Chrome. If it shows LISTENING on 127.0.0.1:9223, then the portproxy may be stale — reset it:
```bash
/mnt/c/Windows/System32/netsh.exe interface portproxy delete v4tov4 listenport=9222
/mnt/c/Windows/System32/netsh.exe interface portproxy add v4tov4 listenport=9222 connectport=9223 connectaddress=127.0.0.1
```

**Two CDP approaches** (both work; try Option A first, fall back to Option B):
- **Option A (Playwright `connect_over_cdp`)** — cleaner API, but may time out on Chrome 148+ during websocket handshake
- **Option B (raw CDP websocket)** — lower-level, always works when Playwright hangs. See Step 2 for code.

If Chrome is not running, the enrichment falls back to web search (less reliable — may hit CAPTCHAs).

The CDP URL is `http://$(ip route show default | awk '{print $3}'):9222`.
See the `browser-use` skill for full setup.

## Enrichment Workflow

For each person/company discovered in the interaction:

### Step 1: Check if person exists in brain

Look for `~/brain/persons/<firstname-lastname>.md`. Use search_files if unsure of slug.

If file exists:
- Read it to see what info is already filled (LinkedIn, role, company, etc.)
- Skip to Step 3 (add timeline entry)

### Step 2: Create person file

**Phase 1 — Web search (general intel, ~30s)**

Before touching LinkedIn, run a web search to get the big picture:

```bash
web_search "First Last Company role"
web_extract "company-website.com/about"
```

Target fields:
- **Company** — name, website, industry (confirm or discover)
- **cross-reference**: if email says one company, web search may reveal they've moved)
- **Role / title** — if the email signature says "VP" but web says "Director", flag it
- **News / recent context** — recent hires, promotions, conference talks, press releases
- **Background** — education, publications, previous roles (readily found on their company bio page

Write down what you find and flag any discrepancies.

**⚠️ web_extract fallback:** If `web_extract` fails (returns error or empty), try the Jina AI Reader first — it's free and works on most sites:
```bash
~/.hermes/scripts/jina-extract.sh "company-website.com/about"
```
If Jina also fails (JS-heavy or blocked site), fall back to browser navigation:
```bash
web_search "First Last Company role"
browser_navigate "company-website.com/about"
browser_snapshot   # for text-heavy pages
browser_vision "Extract company info, team page, about section"  # for SPA pages
```
The browser is slow (~15s vs ~5s for Jina) but works for SPA-heavy sites.

**Phase 2 — LinkedIn for depth (~30-60s)**

After web search, fill in gaps from LinkedIn:

**Fast lookup: Direct profile URL (try first, ~10s)**

Most LinkedIn profiles follow `linkedin.com/in/[firstnamelastname]` (lowercase, no spaces/hyphens). Use the one-shot script:

```bash
cd ~/.hermes/browser-use-env && ./bin/python ../skills/productivity/profile-enrichment/scripts/linkedin-profile.py "First Last"
```

The script (in `scripts/linkedin-profile.py` under this skill) tries the direct URL, falls back to search if 404, and dumps the profile to stdout. This is the preferred approach.

**Manual CDP (fallback when direct URL doesn't work):**

> **⚠️ Playwright connect_over_cdp may time out on Chrome 148+.** If you see
> `Timeout 10000ms exceeded.` after `<ws connected>`, switch to the raw CDP
> WebSocket approach (see `browser-use` skill's
> `scripts/cdp-raw-agent.py` and `references/cdp-raw-websocket.md`).

**Option A: Playwright (default):**

```python
# Using Playwright connect_over_cdp to access real Chrome (logged into LinkedIn)
from playwright.async_api import async_playwright

CDP_URL = "http://172.31.176.1:9222"  # Or dynamically: http://$(ip route | awk '/default/ {print $3}'):9222

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]
    page = await context.new_page()
    
    # Option A: Navigate directly to a known LinkedIn profile URL
    # await page.goto("https://www.linkedin.com/in/username/", wait_until="domcontentloaded")
    
    # Option B: Search LinkedIn (if you only have name + company)
    await page.goto("https://www.linkedin.com/search/results/people/?keywords=First+Last+Company", wait_until="domcontentloaded")
    await asyncio.sleep(2)
    
    # Extract visible profile info
    name = await page.title()
    # Or use page.evaluate() to extract DOM
    
    await browser.close()
```

**Option B: Raw CDP WebSocket (when Playwright times out):**

**⚠️ Use `window.location.href` NOT `Page.navigate` on Chrome 148+ — see Chrome 148+ CDP Navigation section below.**

```python
import asyncio, json, urllib.request, websockets

CDP_HTTP = "http://172.31.176.1:9222"

# Find a LinkedIn search results tab (NOT tracker tabs like merchantpool/demdex)
resp = urllib.request.urlopen(CDP_HTTP + "/json")
pages = json.loads(resp.read())
target = next((p for p in pages if "/search/results/people" in p.get("url", "")), None)
if not target:
    target = next((p for p in pages if "about:blank" in p.get("url", "")), None)
if not target:
    # Fallback to first non-chrome, non-tracker tab
    for p in pages:
        url = p.get("url", "")
        if url and not url.startswith("chrome://"):
            if not any(k in url for k in ["merchantpool", "demdex", "protechts", "fbsbx"]):
                target = p
                break

async with websockets.connect(target["webSocketDebuggerUrl"],
                              max_size=2**20, ping_interval=None) as ws:
    # Navigate via window.location.href (keeps WS alive on Chrome 148+)
    search_url = "https://www.linkedin.com/search/results/people/?keywords=First+Last+Company"
    cmd = json.dumps({"id": 1, "method": "Runtime.evaluate",
                      "params": {"expression": f"window.location.href = '{search_url}'",
                                 "returnByValue": True}})
    await ws.send(cmd)
    await asyncio.sleep(3)
    
    # Extract page text
    cmd = json.dumps({"id": 2, "method": "Runtime.evaluate",
                      "params": {"expression": "document.body.innerText",
                                 "returnByValue": True}})
    await ws.send(cmd)
    resp = json.loads(await ws.recv())
    text = resp["result"]["result"]["value"]
    print(text[:2000])
```

### Chrome 148+ CDP Navigation: window.location.href

On Chrome 148+, `Page.navigate` drops the WebSocket after 1-2 navigations (the renderer destroys the WS endpoint on page change). **Use `window.location.href` via `Runtime.evaluate` instead** — the WS stays alive indefinitely:

```python
async def nav_and_wait(ws, url, wait=4):
    safe = url.replace("'", "\\'")
    cmd = json.dumps({"id": 1, "method": "Runtime.evaluate",
                      "params": {"expression": f"window.location.href = '{safe}'",
                                 "returnByValue": True}})
    await ws.send(cmd)
    await asyncio.sleep(wait)
    # Then evaluate to get current URL
    cmd2 = json.dumps({"id": 2, "method": "Runtime.evaluate",
                       "params": {"expression": "window.location.href", "returnByValue": True}})
    await ws.send(cmd2)
    resp = json.loads(await ws.recv())
    return resp["result"]["result"]["value"]
```

Connect once to a **non-tracker tab** (LinkedIn search results tab, Facebook tab, or about:blank) and reuse it for the whole session. Trackers like LinkedIn merchantpool/demdex/protechts reject all navigation silently.

See `browser-use` skill's `references/cdp-raw-websocket.md` for detailed WS caveats.

**Option C: Existing-tab extraction (Chrome 148+ fallback)**

When both CDP methods hang (common on Chrome 148+), check if a tab already has the target LinkedIn profile loaded — skip navigation entirely, just connect and extract. This bypasses both the Playwright timeout and the raw CDP navigation hang.

See `references/cdp-existing-tab-extraction.md` for full code.

If Chrome CDP is unavailable, all CDP methods fail, and no existing tab has the profile, fall back to web search:
```bash
# Search for "First Last Company linkedin"
# Search for "First Last Company role title"
```

**Phase 3 — Apollo Enrichment (~15s, structured data fill)**

After web search and LinkedIn research, use Apollo.io to fill in structured data gaps (industry, revenue, employee count, phone, verified email). Apollo returns data fast without browser overhead.

**IMPORTANT: Apollo Email Pattern Detection Flow**

When enriching multiple contacts from the same company, ALWAYS use Apollo to find the email pattern FIRST, then apply it to contacts that Apollo doesn't have:

1. **Look up 1-2 known contacts per company** via `people/match` to find their verified emails
2. **Identify the pattern** from the verified results (e.g. `first_last@`, `firstlast@`, `first.last@`, `first@`)
3. **Apply the most common pattern** to remaining contacts who weren't found in Apollo
4. **If Apollo shows multiple patterns** (e.g., `firstlast@` for Person A but `first@` for Person B), list both and use the most common one as the primary estimate
5. **If ALL Apollo lookups return empty** (no one from that company in Apollo's database), fall back to data from RocketReach/LeadIQ or general company email format databases

```bash
# Step 1: Find pattern — lookup 1-2 contacts
curl -s "https://api.apollo.io/api/v1/people/match" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"domain": "company.com", "first_name": "First", "last_name": "Last"}' | \
  python3 -c "import sys,json; p=json.load(sys.stdin).get('person',{}); print(f'Email: {p.get(\"email\",\"none\")}, Status: {p.get(\"email_status\",\"none\")}')"

# Step 2: Apply pattern — extract username format
# Example: linda_chen@bonia.com → first_last@ pattern
# Apply: john_doe@bonia.com for all unmatched contacts

# Enrich company — search by name
curl -s "https://api.apollo.io/api/v1/organizations/search" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q_organization_name": "Company Name", "per_page": 1}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); org=d.get('organizations',[{}])[0]; print(f'Industry: {org.get(\\\"industry\\\",\\\"\\\")}\\nEmployees: {org.get(\\\"estimated_num_employees\\\",\\\"\\\")}\\nLinkedIn: {org.get(\\\"linkedin_url\\\",\\\"\\\")}\\nPhone: {org.get(\\\"phone\\\",\\\"\\\")}\\nFounded: {org.get(\\\"founded_year\\\",\\\"\\\")}\\nTicker: {org.get(\\\"publicly_traded_symbol\\\",\\\"\\\")}')\"

# Match a person by name + company domain (preferred) or organization_name
curl -s "https://api.apollo.io/api/v1/people/match" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"domain": "company.com", "first_name": "First", "last_name": "Last"}' | \
  python3 -c "import sys,json; p=json.load(sys.stdin).get('person',{}); print(f'Title: {p.get(\\\"title\\\",\\\"\\\")}\\nEmail: {p.get(\\\"email\\\",\\\"\\\")}\\nStatus: {p.get(\\\"email_status\\\",\\\"\\\")}\\nLocation: {p.get(\\\"city\\\",\\\"\\\")}, {p.get(\\\"state\\\",\\\"\\\")}, {p.get(\\\"country\\\",\\\"\\\")}\\nLinkedIn: {p.get(\\\"linkedin_url\\\",\\\"\\\")}\\nHeadline: {p.get(\\\"headline\\\",\\\"\\\")}')\"
```

**Note:** Apollo returns whatever it has — some fields may be null for smaller/private companies. Cross-reference with web search + LinkedIn. Use `organizations/search` for company intel and `people/match` for person intel. `people/search` (bulk) is blocked on this key.

**Pattern detection strategy for mixed results:** When Apollo returns verified emails with different formats for the same company domain (e.g., `kellychin@parkson.com.my` and `christina@parkson.com.my`), the company uses multiple patterns. In this case:
- Use the shorter/more common pattern as the primary estimate
- Flag remaining contacts as "estimated" in contact profiles

Append Apollo findings to the person/company files.

See `references/apollo-email-pattern-detection.md` for real examples and mixed-pattern handling.

Create `~/brain/persons/<firstname-lastname>.md` with frontmatter:

```yaml
---
tags: [person, contact]
email: person@example.com
company: Company Name
role: Job Title
linkedin: https://linkedin.com/in/username
first_seen: YYYY-MM-DD
source: email|calendar|meeting
---
```

Include all known info:
- Full name, email, company, role
- LinkedIn URL (from web search)
- Company website
- Phone if available
- Relationship type (partner, vendor, customer, candidate, etc.)
- First interaction context

### Step 3: Add timeline entry

Append to the person file:

```markdown
## Timeline
- YYYY-MM-DD | [Interaction context]. [Source: Gmail / Calendar / Meeting]
```

### Step 4: Enrich company file

Also check/create `~/brain/companies/<company-name>.md`:

```yaml
---
tags: [company]
website: https://example.com
email_domain: @example.com
industry: 
first_seen: YYYY-MM-DD
source: email|calendar|meeting
---
```

Add web-researched info and a timeline entry. **ALWAYS include a LinkedIn check for companies too:**

1. **LinkedIn company page** — search `web_search "Company Name linkedin"` or `web_search "site:linkedin.com/company Company Name"` to find the company's LinkedIn presence. Even if no company page exists (private companies often don't have one), this is useful info to note.
2. **Founder/key people search** — search `web_search "Company Name founder"` and `web_search "site:linkedin.com Company Name"` to discover key people. Cross-reference founder info in the company file.
3. **Stock ticker** (if publicly listed) — e.g. KLSE:PRIVA (0123)
4. **Financial data** — revenue, growth, key metrics (often on homepage or investor section)
5. **Subsidiaries & IPs** — from company website's "Our Companies" section
6. **Leadership/Board** — from the website's leadership page
7. **Recent news** — from Google News search snippets

For smaller/private companies, capture what's available (website, industry, location, size if mentioned).

**When enriching a person who is a senior exec/CTO at a company:** Include a Company Profile section in the person file — it frames the relationship and saves CH from asking "what do they do?":

```markdown
## Company Profile
- **Company:** Full Name (Ticker)
- **Industry:** 
- **2025 Revenue:** RM XM (X% YoY)
- **Subsidiaries:** ...
- **Leadership:** ...
```

```markdown
## Timeline
- YYYY-MM-DD | [Interaction context]. [Source: Gmail / Calendar / Meeting]
```

### Step 5: Skip rules (do NOT enrich)

- **Internal Your Company/ITMAX staff** — Jason Cham, Azmin Farhana, Dean Hariz, Kunna, Sarah Ghalibah, Syazwan, Paul, Anwar, Kayana, Iskandar, and anyone @your-domain.com
- **noreply / notifications / no-reply** senders — automated systems
- **CH himself** — Admin Lim in events
- **Newsletters** — unless clearly business-relevant
- **Recurring weekly syncs** — already enriched, just add timeline entry
- **All-day calendar events** — "Home", "Office", "Out of office", "Birthday"

## Personal Contact Enrichment (Facebook Friends / Social Exports)

When enriching personal contacts from Facebook, LinkedIn connections exports, or other social sources, use a different output path and lighter touch:

### Output Path
- Write to `~/brain/friends-and-family/<slug>.md` — NOT `~/brain/persons/`
- This folder is isolated from the CRM/people directory (sales team has no access)
- Create a `README.md` index with a table: names, friend-since dates, profiles found

### Person File Template (Personal)
```markdown
---
tags: [friend, facebook]
facebook_friend_since: Apr 20, 2026
source: facebook_export
enriched: 2026-05-30
---

# Kai Yong Kang (江闓荣)

> Startup Ecosystem Evangelist at AWS · Co-Founder · GenAI Fund

## Facebook Friendship
- **Friend Since:** Apr 20, 2026
- **Source:** Facebook data export

## Contact Information
- **Company:** Amazon Web Services (AWS) · GenAI Fund · Stackforce
- **Role:** Startup Ecosystem Evangelist (AWS) / Partner (GenAI Fund)
- **LinkedIn:** https://linkedin.com/in/kaiyongkang
- **Location:** Vietnam (based), previously Kuala Lumpur

## Background
- Startup ecosystem leader in Southeast Asia & Pakistan
- Focused on AI, cloud technology, startup acceleration

## Relationship
- **Connection:** Tech ecosystem · AWS startup relations

## Timeline
- Apr 20, 2026 | Added as Facebook friend.
- May 30, 2026 | Enriched via web search.

---
*Enriched: 2026-05-30 · Source: web_search*
```

### Batch-First Workflow

When processing a large batch from an export (e.g. 36 Facebook friends), split the work:

1. **Write all base files first** — one pass across all names, creating the base `.md` files with frontmatter, friendship info, and placeholder sections. This is fast (<30s for 36 people).
2. **Then enrich in parallel batches** — use 3 parallel subagents or batch web searches (4 calls at a time) to find LinkedIn/company data, then update each file. Batch enrichment is the slow part because of web search latency.
3. **Wrap up with a README index** — summary table of all processed friends.

This avoids the inefficient pattern of create-one → enrich-one → repeat.

### Web-Search-Only Enrichment (No Chrome CDP Available)

When Chrome CDP is NOT running (Chrome_Debug.bat wasn't launched), do a lighter enrichment using only `web_search`. This is the normal fallback:

1. **Batch search** — search 4 names at a time using parallel `web_search` calls to save turns
2. **Query format**: `web_search "First Last Malaysia LinkedIn"` — add "Malaysia" or the likely country to narrow results
3. **LinkedIn profiles** — when `web_search` returns LinkedIn profile snippets from Apollo/Adapt.io, extract: company, role, location, connections count, education
4. **Common-name disambiguation** — when multiple LinkedIn profiles match, note all possibilities and flag with `"verify with CH"`
5. **No-profile found** — write "(Not found)" and move on in ~10s; don't chase
6. **Append findings** — read the existing file, update `## Contact Information` and `## Background`, add a timeline entry
7. **Batch pacing** — 12 people per turn → ~4 web_search calls (3 names each) + file updates. Easier to manage than 36 in one shot.
8. **Rapid-fire names** — if many friends were added on the same date (e.g. Oct 01, 2025 batch of 12), they likely know each other — treat as a cohort

### Priority Selection
When CH says "priority batch" from a large list of Facebook friends:
- Sort by friend-since date (most recent first) using proper datetime parsing
- 2026 + 2025 = typical priority tier (~36 people for a 1,500-person export)
- Recent friends are more likely to be active relationships worth enriching

### Pitfalls (Personal Enrichment)
- **Don't overwrite `~/brain/people/`** — personal contacts live in `friends-and-family/`, NOT `people/`
- **Common Malaysian/SE Asian names** — Tan, Lim, Goh, Lee, Chew, Chua are very common. Multiple profiles on LinkedIn is normal. Flag uncertainty rather than guessing wrong
- **Facebook friend-since dates may be same-day batches** — don't assume same-date adds are related unless names/location overlap
- **Oct 01, 2025 batch** was a LinkedIn contacts sync batch (many added simultaneously) — these are higher-value connections, spend more time on them
- **CDP LinkedIn scraping for mutual connections** — use `window.location.href` via `Runtime.evaluate` (NOT `Page.navigate`) to keep WS alive on Chrome 148. Use a LinkedIn search results tab as the reusable tab — tracker tabs (merchantpool, demdex, protechts) reject all navigation. Connect once, navigate dozens of profiles.
- **Education extraction** — LinkedIn renders education names in plain text after the "Education" heading. Text-based scanning (`body.innerText` split by "\n") is more reliable than CSS selectors which break when LinkedIn changes class names.

## Company Extraction from Email

| Source | How to Extract |
|--------|---------------|
| Email signature block | Look for company name after role title |
| Email domain | @portainer.io → Portainer, @aws.amazon.com → AWS |
| Email thread quoted text | Previous messages contain company names |
| Meeting event title | "Portainer x Your Company" → Portainer |
| Meeting transcript | Implicit from conversation context |

## Person File Template

```markdown
---
tags: [person, contact]
email: neil.cresswell@portainer.io
company: Portainer
role: VP of Engineering
linkedin: https://linkedin.com/in/neilcresswell
first_seen: 2026-05-05
source: email
---

# Neil Cresswell

## Contact Information
- Email: neil.cresswell@portainer.io
- Company: Portainer
- Role: VP of Engineering
- LinkedIn: https://linkedin.com/in/neilcresswell
- Website: https://portainer.io

## Relationship
- **Connection:** Partner (Docker/container management)
- **First Interaction:** 2026-05-05 (Portainer x Your Company meeting)

## Timeline
- 2026-05-05 | Meeting: Portainer x Your Company / ITMAX — discussed container management for surveillance infrastructure. [Source: calendar]

## Notes
- Key decision-maker for technical partnerships
```

## Company File Template

```markdown
---
tags: [company]
website: https://portainer.io
email_domain: @portainer.io
industry: DevOps / Container Management
first_seen: 2026-05-05
source: calendar
---

# Portainer

## Contact Information
- Website: https://portainer.io
- LinkedIn: https://linkedin.com/company/portainer
- Industry: DevOps, Container Management

## Relationship
- Docker container management platform
- Used by Your Company for edge deployment infrastructure
- Key contact: Neil Cresswell (neil.cresswell@portainer.io)

## Timeline
- 2026-05-06 | Email contact established via renewal discussion
- 2026-05-05 | Neil Cresswell meeting — container management for surveillance. [Source: calendar]
```

## Web Research Tips

- **Start with web search first** — `web_search "First Last Company role"` gives you company context, role confirmation, and news before you dive into LinkedIn
- **Then LinkedIn for depth** — once you know who they are, `linkedin.com/in/[firstnamelastname]` fills in career history, education, mutual connections
- **Then Apollo for structured data fill** — `organizations/search` + `people/match` fills in industry, revenue, employee count, verified email, phone — data you can't easily get from a profile page
- Cross-reference multiple sources — don't trust one result
- If you can't verify a detail, leave it blank rather than guessing wrong
- Ask CH directly when unsure — faster and more accurate
- When the user shares a Google Slides company profile deck, use `references/slide-deck-extraction.md` to extract text content from each slide

### Content Extraction — Fallback Chain

When extracting content from company websites or bio pages, use this priority order. Move to the next step immediately when the current one fails — don't retry:

| Priority | Method | Speed | When to Use |
|----------|--------|-------|-------------|
| 1st | `web_extract` (ddgs by default) | ~5s | Fastest, works on most sites |
| 2nd | `jina-extract.sh` (Jina AI Reader) | ~5s | When web_extract errors; free, no auth, works on most sites that block direct extraction |
| 3rd | `browser_navigate` + `browser_snapshot` | ~15s | When Jina also fails (JS-heavy, auth-walled sites) |
| 4th | `browser_navigate` + `browser_vision` | ~15s | When page is a SPA (snapshot truncates, JS-heavy) |
| 5th | Skip extraction, note in file | — | When browser also blocked (CAPTCHA, Cloudflare) |

**When web_extract fails:**
- Common error patterns: `AUTH_ERROR`, `Unauthorized`, `timeout`, `402 Payment Required`, `out of credits`
- **Firecrawl credit exhaustion** — if using Firecrawl and you get "out of credits" or 402 errors, switch to ddgs (DuckDuckGo): `hermes config set web.backend ddgs` in the active profile and restart the gateway. ddgs is free with no API key or credit limits. If you're already on ddgs, proceed to fallback #2.
- First fallback: `~/.hermes/scripts/jina-extract.sh "<url>"` (free, no auth needed)
- If Jina also blocked: navigate directly with the browser instead
- If the browser also fails (CAPTCHA, Cloudflare), skip extraction and just note "Web research unavailable — pending manual review" in the person file

See `references/content-extraction-fallback.md` for detailed error patterns and per-site-type extraction strategies.
See `references/document-to-brain-enrichment.md` for the full pipeline when enriching from an uploaded company/person PDF deck (archive → pymupdf extract → cross-reference all brain files). Covers multi-partner YAML in deal frontmatter too.

See `references/firecrawl-api-usage.md` for Firecrawl CLI commands, direct curl API usage, and key management. When Firecrawl is out of credits, switch `web.backend` to `ddgs` (DuckDuckGo) — free, no API key needed.
See `references/friends-family-enrichment.md` for a Facebook friends export enrichment session with common-name disambiguation notes, query patterns, and known profile results.
See `references/remote-chrome-launch.md` for troubleshooting Chrome CDP connection failures and launching Chrome from WSL.
See `references/spreadsheet-contact-enrichment.md`.

### Quick Business Card Ingestion (Lightweight)

When the user sends business card photos with "add to my brain" — a faster, lighter workflow than full enrichment. Just archive the image, create contact files from the card data, deduplicate, and crosslink into a meeting note. See `references/business-card-ingestion.md`.

### Dealing with Search Engine Blocks

Search engines frequently block automated browser sessions:
- **Google:** Blocks after ~2 searches with CAPTCHA
- **Bing:** Cloudflare challenges on some queries
- **DuckDuckGo Lite & HTML:** Bot detection also blocks

**With browser-use CDP, search engine blocks are largely irrelevant** — you navigate LinkedIn directly in a real Chrome session.

**When CDP is unavailable or you need company data (not LinkedIn):**
1. Navigate directly to the company's website — most company sites don't have bot protection
2. Use the site's own navigation/menu to find leadership, about, or news sections (many sites are SPAs where menu clicks work but direct URLs 404)
3. If the site uses a single-page-app pattern where `browser_snapshot` truncates content, use `browser_vision` to extract what's visible on screen
4. For financials of public companies, check the company website's investor/AR section directly

### Company Website Patterns
- Many Malaysian company sites (especially SPA-built ones) use hash-based or JS-navigation where direct subpage URLs return 404 but clicking menu items works
- Always try the menu sidebar first — it's often more reliable than guessing URL paths
- The homepage often contains financial highlights, subsidiary info, and news — scroll down as pages frequently load content progressively

## Event-Sourced Lead Tracking

When an interaction comes from a **trade show, conference, or networking event** (e.g., NRF, CES):

### Before creating any files

1. **Confirm the event name** with CH if not obvious from context
2. **Business card scanning** — if the lead arrives as a photo of a business card, use `vision_analyze` to extract name, title, company, phone, email. Cross-reference what the user says vs what the card shows. See `references/event-lead-tracking.md` → Business Card Scanning section for full workflow.
3. **Create or update a leads tracker** at `~/brain/{event-name}-leads-tracker.md`:

```markdown
# {Event Name} Leads Tracker

**Source:** event
**Tag:** {event-name-short}
**Tracking period:** {dates}

## Leads

| # | Company | Contact | Profile Saved | Notes |
|---|---------|---------|---------------|-------|
| 1 | {Company} | {Name} ({Role}) | brain/companies/{slug}.md | Key context |
```

3. **Tag ALL profiles** with `source: event` and `tag: {event-name}` in the frontmatter:

```yaml
---
source: event
tag: {event-name}
lead_owner: user (Your Company)
first_contact: {Name} ({Role})
---
```

### Which files get the tag

- **Company profile** (`~/brain/companies/{slug}.md`) — add source + tag + lead_owner to the header
- **Contact/person profile** (`~/brain/persons/{slug}.md`) — add source + tag + lead_owner + company

### Tracker file format

Keep the tracker simple — a table with: number, company, contact (name + role), whether profile files were saved, and key context notes. The tracker lives as a standalone .md in `~/brain/` so it's searchable and persisted.

### Duration

The source/tag assignment applies for the duration CH specifies (typically a few days after the event). After the period expires, leave the existing tags in place — they're historical metadata, not active constraints.

### Example: NRF Event

```yaml
# In the company or person file
source: event
tag: NRF
lead_owner: user (Your Company)
first_contact: T-Tutt Jungkankul (CEO)
```

See `references/event-lead-tracking.md` for the full NRF example with tracker template.

## Pitfalls

- **Never save contacts as a single consolidated file** — each person gets ~/brain/persons/<name>.md and each company gets ~/brain/companies/<name>.md. A single "AWS Event Contacts.md" file is the wrong format. Always split into individual files.
- **Exception — spreadsheet enrichment:** When CH provides an xlsx event contacts file and asks to fill in missing emails/LinkedIn, do NOT create brain files. Fill the spreadsheet in place. See `references/spreadsheet-contact-enrichment.md`.
- **Don't enrich internal staff
- **Don't use Google/Bing Programmable Search** — they block automated queries. Use browser navigation for web searches
- **Don't overwrite existing person files** — append timeline entries, don't replace
- **Don't spend too long** — 2-3 minutes per person is sufficient. "Good enough" enrichment
- **Web-first order** — search first for company/role/news context (~30s), then LinkedIn for career depth (~30s). Don't skip the web search step
- **Don't enrich system/noreply emails** — filtered in Step 5
- **Don't enrich the same person twice in a day** — check the existing file first
- **Apollo API key from bashrc, never hardcode in scripts** — the key is in `~/.bashrc` as `export APOLLO_API_KEY=...`. Always source it (`source ~/.bashrc`) before Apollo calls in scripts. Hardcoding the raw key inline (in Python scripts, curl commands) fails because the key is only ~22 chars and looks truncated when pasted. Always pass via environment variable: `APOLLO_API_KEY="$APOLLO_API_KEY" python3 script.py` or `export APOLLO_API_KEY` before running.
- **Apollo `people/match` key length quirk**: The key is only ~22 chars (not the typical 40+ char API key format). This is correct — do NOT assume it's truncated. When testing from terminal `curl` commands, it works fine. When calling from `execute_code` or `delegate_task` Python subprocesses, the key must be passed through the environment (not embedded in the script) because the subprocess context may not source bashrc automatically. Always test with `echo ${#APOLLO_API_KEY}` to confirm the key length is 22, then export it explicitly before running the script.
- **Apollo people/match hit rate**: typically 40-60% for SEA retail contacts. Names with special characters, small private companies, and non-English names often return empty. This is normal — accept the gap.

**CRITICAL: Apollo "verified" emails can still bounce.** Apollo's `email_status: verified` means the email was valid at some point — but the returned email may use a **different domain or format** than the one you queried against. ALWAYS:
- **Inspect the ACTUAL email string** returned by Apollo, not just the status flag. Compare it to your inferred pattern.
- **Check the domain** — e.g., searching by `bonia.com` may return `shinny.tan@boniacorp.com` (different domain). The domain you search with does not guarantee the result domain.
- **Cross-reference all returned emails from the same company** — if Person A gets `@domain1` and Person B gets `@domain2`, the company uses multiple domains. Document both.
- **Before finalising any draft**, verify EVERY contact individually via `people/match`. Do not apply a single inferred pattern to all unmatched contacts without checking.
- **When Apollo returns empty for ALL contacts** at a company, use NeverBounce email format search via `web_search "{company} email format"` to find aggregated pattern data.

**Bounce handling**: If CH reports bounces after sending:
1. Re-verify the bounced addresses immediately via Apollo `people/match`
2. Compare the returned email string to what was sent — look for domain mismatches
3. Try alternative patterns (`first.last@` vs `first_last@` vs `firstl@`) if Apollo returns no match
4. Check aggregated format databases (NeverBounce, RocketReach, LeadIQ) for the company's pattern
5. Update the contact profile with the correction and re-save the draft

See `references/apollo-bounce-prevention.md` for real bounce incidents and the prevention checklist.
- **Batch enrichment pacing**: 25 contacts at ~30s each takes ~15 min. Break into groups of 8-12 per turn for readability.
- **LinkedIn authwall largely bypassed** — browser-use CDP uses your real Chrome session, so you're logged into LinkedIn. If you still hit an authwall (session not copied to debug profile), ask CH to log into LinkedIn in the Chrome window
- **Chrome CDP must be running before enrichment** — if Chrome isn't launched with debug flags, CDP connection fails. Check with `curl -s http://GW:9222/json/version` first
- **Playwright connect_over_cdp may time out on Chrome 148+** — WebSocket connects but CDP handshake hangs. Switch to **Option B: Raw CDP WebSocket** (code in Phase 2) using the `websockets` library directly. **Note:** Even Option B may hang on `Page.navigate` (`.frameStoppedLoading` never fires). When that happens, use **Option C: Existing-tab extraction** — search existing tabs for the target profile URL/title and extract directly without navigation.
- **LinkedIn SPA timeout** — use `wait_until="domcontentloaded"` not `networkidle`. LinkedIn never finishes `networkidle` within reasonable timeout
- **Page.evaluate for extraction** — use `page.evaluate()` to extract innerText from LinkedIn profile selectors rather than relying on snapshot text (which truncates for long pages)
- **Search engine CAPTCHA** — Google blocks after ~2 searches, Bing has Cloudflare on some queries. Don't keep retrying — switch to direct website navigation immediately
- **Skip financial/investor bot-protected sites** — i3investor, SimplyWallSt, StockAnalysis all use Cloudflare bot detection. Don't waste time attempting them
- **Yahoo Finance doesn't resolve KLSE stocks** — Bursa Malaysia stocks aren't found on Yahoo Finance with the .KL suffix
- **SPA website gotcha** — many Malaysian company sites use single-page-app architecture. Menu clicks work but direct subpage URLs return 404. Always try the menu sidebar first
- **Apollo.io API key tier limitations** — the API key is in `~/.bashrc` as `export APOLLO_API_KEY=...`. Use curl directly with `X-Api-Key` header — there is no wrapper script. Tested endpoints:
  - `organizations/search` — FULL DATA: industry, employees, revenue, phone, LinkedIn, keywords, location ✅
  - `organizations/enrich` — works by domain ✅
  - `people/match` — matches by name + company ✅
  - `contacts/search` — returns existing contacts ✅
  - `auth/health` — healthy check ✅
  - `people/search` — API_INACCESSIBLE (even on paid tier; may need key regeneration) ❌
  - `mixed_people/search` — API_INACCESSIBLE ❌
  
  Always test with `curl -s -o /dev/null -w "%{http_code}" "https://api.apollo.io/api/v1/$endpoint" -H "X-Api-Key: $KEY"`. Key goes in `X-Api-Key` header, NOT request body. See `references/apollo-endpoint-results.md` for full test data.
- **Fallback when Apollo isn't available** — when people search is inaccessible, use browser navigation: `web_search` or direct company LinkedIn pages. Browser-based LinkedIn search works fine without Apollo.
- **Sites change layout** — scroll down fully before giving up; homepages frequently contain all key data in one scrollable page
- **Bursa company name** — use "Privasia Technology Berhad" (full registered name), not just "Privasia" for company files
- **Paywalled data sources — skip fast** — EMIS, D&B Hoovers, i3investor, SimplyWallSt, and similar financial data platforms gate their actual data behind paywalls/subscriptions. The `web_extract` content may confirm the page is a profile but yield zero data. Detect this quickly: if the extracted content is mostly form fields, pricing, or login prompts rather than company data, **move on** — don't retry or attempt workarounds. Public companies have free data available elsewhere (Bursa Malaysia website, annual reports, company investor pages).
- **Multi-entity companies** — some companies operate under multiple registered entities (e.g. "Farmasi C S (Station 18) Sdn Bhd" vs "Farmasi C S Sdn Bhd" vs "Farmasi C S (Ipoh Garden) Sdn Bhd"). Different entities may have different industries and financials. When building a company profile, list all known entities and flag which one the interaction relates to. Prefer the primary trading entity.
- **Unprocessed directory screenshots** — When the user sends directory screenshots they land in `~/.hermes/image_cache/` as `.jpg` files. If the user says "you just helped research these" and you can't find the contacts, check `~/.hermes/image_cache/` for unprocessed images before searching session history. This is the #1 cause of "I can't find those contacts" errors.
- **Unknown contacts — ask immediately** — When the user asks you to draft emails for companies you have no contact data for, do NOT search session history or the tracker endlessly. First check `~/.hermes/image_cache/` for unprocessed screenshots. If none found, say "I don't have contacts for those — do you have names/screenshots?" immediately.
- **Unknown contacts — ask immediately** — When the user asks you to draft emails for companies you have no contact data for, do NOT search session history or the tracker endlessly. Say "I don't have contacts for those — do you have names/screenshots?" immediately. Wasting turns searching for data that doesn't exist frustrates the user.
- **Apollo `domain` parameter preferred over `organization_name`** — `people/match` works more reliably when you pass the company's primary domain (e.g., `"domain": "parkson.com.my"`) rather than `organization_name`. The domain parameter disambiguates better for common company names. Always try `domain` first, fall back to `organization_name` if the lookup returns empty.
- **Apollo `people/match` also returns company data** — The response includes a full `organization` object with industry, employee count, phone, revenue, technology stack, LinkedIn URL, and description. Check this before making a separate `organizations/search` call — it often saves an extra API call.
- **Unprocessed directory screenshots** — When the user sends directory screenshots, they land in `~/.hermes/image_cache/` as `.jpg` files. If the user says "you just helped research these" and you don't see the contacts, check `ls -lt ~/.hermes/image_cache/*.jpg` for unprocessed images. This is the #1 cause of "I can't find those contacts" errors.
- **Email pattern fallback when Apollo has no data** — When Apollo returns empty for ALL contacts at a company, use these secondary sources in order: (1) NeverBounce email format search via `web_search "{company} email format"`, (2) RocketReach/LeadIQ format databases, (3) AeroLeads email format pages. These give aggregated patterns (e.g., "26% use first.last@") even when Apollo can't match specific people.
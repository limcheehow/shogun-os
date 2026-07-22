# Apollo.io Endpoint Test Results

Tested against CH's new Apollo API key on 2026-05-21. Key stored in `~/.bashrc` as `APOLLO_API_KEY`. All curl commands use `X-Api-Key` header auth.

## Working Endpoints

### `organizations/search` — ✅ Full Data
Sample query: `{"q_organization_name": "ITMAX", "per_page": 1}`
Returns: industry (information technology & services), employees (180), ticker (5309.KL), LinkedIn URL, phone, founded year (2001), 40+ keyword tags
**Use for:** Company enrichment during profile research. Search by company name, domain, or industry.

### `organizations/enrich` — ✅ Works
Sample query: `{"domain": "your-domain.com"}`
Returns: full organization data by domain. Fast single-lookup.

### `people/match` — ✅ Works
Sample query: `{"first_name": "Admin", "last_name": "Lim", "organization_name": "Your Company"}`
Returns: matched person record with ID, name (Chee Lim), email (your-user@your-domain.com, verified), location (Subang Jaya, Selangor, Malaysia).
**Use for:** Quick person lookup when you have name + company. Returns best match, not a list.
**Note:** Title and LinkedIn URL may be null for people not extensively indexed in Apollo.

### `contacts/search` — ✅ Works
Sample query: `{"page": 1, "per_page": 1}`
Returns: existing contacts from the user's Apollo account (first_name, last_name, name, linkedin_url, photo_url, title, etc.)
**Use for:** Checking if a contact already exists in Apollo's CRM.

### `auth/health` — ✅ Works
Returns: `{"healthy": true, "is_logged_in": true}`

## Blocked Endpoints

### `people/search` — ❌ API_INACCESSIBLE
Even though CH is on a paid tier, this endpoint returns HTTP 403 with `{"error":"api/v1/people/search is not accessible with this api_key","error_code":"API_INACCESSIBLE"}`.
**Workaround:** Use `people/match` for single-person lookups. For bulk people search, upgrade to a higher tier or generate a new API key after upgrading.

### `mixed_people/search` — ❌ API_INACCESSIBLE
Same 403 error as `people/search`. Not available on current key.

## Authentication Rules
- **Header:** `X-Api-Key` header (NOT request body — body placement returns `INVALID_API_KEY_LOCATION`)
- **Content-Type:** `application/json`
- **Base URL:** `https://api.apollo.io/api/v1/`

## Quick Test Commands

Env var is set in `~/.bashrc`. For current shell:
```bash
export APOLLO_API_KEY="$APOLLO_API_KEY"  # Get from https://app.apollo.io/#/settings/api
BASE="https://api.apollo.io/api/v1"

# Test org search
curl -s -w "\nHTTP: %{http_code}" "$BASE/organizations/search" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q_organization_name": "Your Company", "per_page": 1}'

# Test people match
curl -s "$BASE/people/match" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Chee", "last_name": "Lim", "organization_name": "Your Company"}'
```

## Parsed Output Commands (used in enrichment pipeline)

These are the exact commands from the `profile-enrichment` Phase 3 step, formatted for manual testing:

```bash
# Company org search — parsed output
curl -s "https://api.apollo.io/api/v1/organizations/search" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q_organization_name": "ITMAX", "per_page": 1}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); org=d.get('organizations',[{}])[0]; print(f'Name: {org.get(\"name\",\"\")}\nIndustry: {org.get(\"industry\",\"\")}\nEmployees: {org.get(\"estimated_num_employees\",\"\")}\nLinkedIn: {org.get(\"linkedin_url\",\"\")}\nPhone: {org.get(\"phone\",\"\")}\nFounded: {org.get(\"founded_year\",\"\")}\nTicker: {org.get(\"publicly_traded_symbol\",\"\")}\nDescription: {org.get(\"short_description\",\"\")[:200]}')"

# Company enrich by domain — parsed output
curl -s "https://api.apollo.io/api/v1/organizations/enrich" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"domain": "your-domain.com"}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin).get('organization',{}); print(f'Name: {d.get(\"name\",\"\")}\nIndustry: {d.get(\"industry\",\"\")}\nEmployees: {d.get(\"estimated_num_employees\",\"\")}\nLinkedIn: {d.get(\"linkedin_url\",\"\")}')"

# People match — parsed output
curl -s "https://api.apollo.io/api/v1/people/match" \
  -H "X-Api-Key: $APOLLO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Chee", "last_name": "Lim", "organization_name": "Your Company"}' | \
  python3 -c "import sys,json; p=json.load(sys.stdin).get('person',{}); print(f'Name: {p.get(\"name\",\"\")}\nTitle: {p.get(\"title\",\"\")}\nEmail: {p.get(\"email\",\"\")} ({p.get(\"email_status\",\"\")})\nLocation: {p.get(\"city\",\"\")}, {p.get(\"state\",\"\")}\nHeadline: {p.get(\"headline\",\"\")}\nLinkedIn: {p.get(\"linkedin_url\",\"\")}')"
```

**Note:** `people/match` uses `first_name` + `last_name` + `organization_name`. It does NOT accept an email field. Returns the single best match, not a list.

## Real-World Variability (tested 2026-05-21)

`people/match` results vary significantly by person. Examples from today:

| Person | Email | Status | Title/Headline | Employment History | LinkedIn |
|--------|-------|--------|---------------|-------------------|----------|
| Admin Lim @ Your Company | your-user@your-domain.com | verified | ❌ null | ❌ sparse | ❌ null |
| Patrick Sim @ Secret Recipe | ❌ null | unavailable | ✅ Group CEO at Secret Recipe | ✅ Full career: PwC→Deloitte→BDO→Secret Recipe (2013→CEO) | ❌ null |
| Flora Chee @ H Space | flora@hspace.co | verified | ❌ null | ❌ sparse | ❌ null |

**Key insight:** Apollo's `people/match` is best for email discovery and location data. For career depth and title/headline, LinkedIn is still essential. Combine Apollo email data with LinkedIn career history for the full picture. Apollo rarely returns LinkedIn URLs in `people/match` — if you need the LinkedIn link, use `web_search` separately.

## Key Insight
Even on a paid tier, people-search endpoints may remain blocked. The tier upgrade may need a **new API key** to be generated. Don't assume upgrading the plan automatically unlocks all endpoints — test with the actual key.
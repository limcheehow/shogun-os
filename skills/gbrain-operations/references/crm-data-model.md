# CRM Data Model — gbrain Supabase Pages

The gbrain's Supabase `pages` table is the single source of truth for all CRM data (deals, companies, contacts). There are no separate CRM tables — everything lives in `pages` with different slug prefixes.

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | PK |
| `slug` | text | Unique path: `deals/<deal-name>`, `companies/<company-name>`, `persons/<person-name>` |
| `title` | text | Display name |
| `type` | text | `page`, `doc`, etc. |
| `page_kind` | text | Subtype hint |
| `frontmatter` | jsonb | CRM-specific fields (see below) |
| `compiled_truth` | text | Full compiled text including all timeline entries |
| `created_at` | timestamptz | When first imported |
| `updated_at` | timestamptz | When last modified |
| `search_vector` | tsvector | Full-text search index |

**Important:** There is NO `category` column. Filter by slug prefix instead:
- `slug LIKE 'deals/%'` → Deals
- `slug LIKE 'companies/%'` → Companies  
- `slug LIKE 'persons/%'` → Contacts/people
- `slug LIKE 'people/%'` → (also has people data)

## Volume (current)

| Type | Count |
|------|-------|
| People/Contacts | ~13,000 |
| Companies | ~4,900 |
| Deals | ~105 |
| Wiki/Notes | ~75 |
| Meetings | ~40 |

## Frontmatter Fields by CRM Type

### Deals (`deals/<name>`)

```json
{
  "stage": "Prospecting | Qualified | Tech Pre-Sales | Quote | Confirmed | Closed Won | Closed Lost",
  "owner": "Anwar Husaini | Kunnasilan Karunanithee | Nurul Liyana Abd Rahman | Liyana | Chee How Lim",
  "amount": 12345.67,
  "hot": "Yes | No",
  "mrr": null,
  "customer": "Company Name",
  "industry": "Retail | Government & NGO | F&B | Healthcare | …",
  "priority": "Low | Medium | High",
  "close_date": "2026-05-15T00:00:00.000Z",
  "created": "2026-01-22T00:00:00.000Z",
  "deal_id": "270519921342",
  "partner": "Canon Marketing | Syspex | Lenovo | …",
  "contact_name": null,
  "contact_email": null,
  "relationship": "customer > tapway | partner > tapway"
}
```

### Companies (`companies/<name>`)

```json
{
  "industry": "Retail",
  "location": "Kuala Lumpur",
  "website": "https://…",
  "size": "50-200",
  "notes": "…"
}
```

### Persons/Contacts (`persons/<name>`)

```json
{
  "email": "person@company.com",
  "company": "Company Name",
  "role": "CTO",
  "phone": "+60…",
  "notes": "…"
}
```

## Query Patterns

All CRM API routes are server-side Next.js handlers. They must use the **service_role key** because the `pages` table has no Row-Level Security policies (the anon key has no SELECT permission).

### Supabase Client Setup

```ts
// lib/supabase.ts — exports TWO clients
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);        // browser
export const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey);    // server
```

### List Deals

```ts
import { supabaseAdmin } from '@/lib/supabase';

const { data, error } = await supabaseAdmin
  .from('pages')
  .select('*', { count: 'exact' })
  .like('slug', 'deals/%')
  .order('created_at', { ascending: false });
```

### Filter by frontmatter field

```ts
// By owner
.like('slug', 'deals/%')
.eq('frontmatter->>owner', 'Anwar Husaini')

// By stage (ILIKE for case-insensitive)
.like('slug', 'deals/%')
.ilike('frontmatter->>stage', '%Won%')

// By amount (numeric comparison)
.gte('frontmatter->>amount', '10000')
```

### Dashboard Stats (aggregation pattern)

```ts
// Fetch all deals, then aggregate in JS (Supabase free tier has no JSONB aggregation functions)
const { data } = await supabaseAdmin
  .from('pages')
  .select('title, frontmatter')
  .like('slug', 'deals/%');

// Then reduce in JS: sum amount, count by stage/owner/priority, etc.
```

### Full-Text Search

```ts
// Across all CRM types
.like('slug', 'deals/%')  // or companies/%, persons/%
.or(`title.ilike.%${term}%,compiled_truth.ilike.%${term}%`)
```

### Semantic Search (via content_chunks table)

The `content_chunks` table has embeddings (pgvector, 1536 dimensions). Join with `pages`:

```ts
// Requires direct SQL via postgres connection (supabaseAdmin doesn't support vector operators)
// Use the crm-search.py script instead for vector search
```

## Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```

The service role key is required for ALL server-side API routes because the `pages` table has no RLS policies.

## Pitfalls

- ❌ **Querying `brain_pages` table** — The table is called `pages`, not `brain_pages`. The old `brain_pages` table was from a previous schema iteration.
- ❌ **Using `eq('category', 'deals')`** — There is no `category` column. Use `like('slug', 'deals/%')` instead.
- ❌ **Using anon key in API routes** — The anon key has no SELECT permission on the `pages` table. Always use `supabaseAdmin` for server-side queries.
- ❌ **`frontmatter` is jsonb but values are strings** — Numeric comparisons need `GTE`/`LTE` on the string value cast. For precise numeric filtering, consider a database view or direct SQL.
- ❌ **`useSession` during static generation** — Next.js builds attempt to statically prerender pages. If a page uses `useSession()`, it crashes during build because there's no SessionProvider context. Fix: remove `useSession` from pages (middleware handles auth redirect), or wrap in a `useEffect` check.
# Next.js 16 + Supabase + Tailwind v4 Project Patterns

> Derived from the your company Product Dashboard project (May 2026). These patterns apply when scaffolding or modifying Next.js 16 + Supabase projects.

## Tailwind v4: CSS-First Config (No tailwind.config.ts)

Tailwind v4 switched from JavaScript config files to **CSS-first configuration** using the `@theme` directive in `globals.css`. There is NO `tailwind.config.ts` — attempting to create or modify one has no effect.

### How brand themes work in v4

```css
/* src/app/globals.css */
@import "tailwindcss";

@theme {
  --color-navy: #1E2D5A;
  --color-navy-dark: #0F1E3D;
  --color-green: #8DC63F;
  --color-green-dark: #5B9B1E;
  --color-grey-light: #F5F5F5;
  --color-grey-mid: #E8E8E8;
  --color-text-mid: #444444;
  --color-text-light: #777777;
  --font-sans: "Poppins", Arial, Helvetica, sans-serif;
  --font-display: "Space Grotesk", sans-serif;
  --radius-brand: 0.12rem;
  --shadow-brand: 0 2px 8px rgba(0,0,0,0.15);
}
```

Usage: `bg-navy`, `text-green`, `font-display`, `rounded-brand`, `shadow-brand`

### Font imports with `next/font`

```tsx
// src/app/layout.tsx
const poppins = Poppins({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-poppins",
})
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-space",
})
// Apply to <html>: className={`${poppins.variable} ${spaceGrotesk.variable}`}
```

The CSS variable `--font-poppins` is then mapped via the `@theme` directive's `--font-sans`.

## Next.js 16: Async cookies() for Supabase SSR

Next.js 16 made `cookies()` from `next/headers` asynchronous — it returns a `Promise<ReadonlyRequestCookies>`. The Supabase SSR client MUST use an async function:

```typescript
// src/lib/supabase/server.ts
import { createServerClient } from "@supabase/ssr"
import { cookies } from "next/headers"

export async function createServerSupabaseClient() {
  const cookieStore = await cookies()  // ⚠️ must await
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

## Supabase REST API: Upsert Pattern for Sync Scripts

For Python scripts that sync data into Supabase tables, use the REST API with `resolution=merge-duplicates`:

```python
HEADERS = {
    "Content-Type": "application/json",
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Prefer": "resolution=merge-duplicates",
}

# Upsert (insert or update by unique constraint)
req = urllib.request.Request(
    f"{SUPABASE_URL}/rest/v1/{table}",
    data=json.dumps([record]).encode(),
    method="POST",
    headers=HEADERS,
)
```

On 409 conflict, fall back to PATCH by slug:
```python
# Update existing record
slug = record["slug"]
update_url = f"{SUPABASE_URL}/rest/v1/{table}?slug=eq.{urllib.parse.quote(slug, safe='')}"
patch_data = {k: v for k, v in record.items() if k not in ("slug", "created_at")}
req2 = urllib.request.Request(
    update_url,
    data=json.dumps(patch_data).encode(),
    method="PATCH",
    headers=HEADERS,
)
```

### Auth: PAT vs Service Role Key

The Supabase **Management API** (for executing SQL) requires a **Personal Access Token (PAT)** — NOT the service_role key. PATs start with `sbp_v0_`. The service_role key is for the **Data API** (table queries via `/rest/v1/`).

- Data API → service_role key from `~/.hermes/supabase_key.txt`
- Management API (SQL) → PAT from existing scripts (check `supabase-brain-sync.py` for hardcoded PAT)

## Docker Multi-Stage for Next.js 16

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.ts ./next.config.ts
EXPOSE 3000
CMD ["npm", "run", "start"]
```

Note: `.env*` files must NOT be included in Docker build context (use `.dockerignore`). Pass secrets via `docker compose` `env_file:` directive pointing to `.env.production`.

## Supabase Adapter with NextAuth v5

```typescript
import { SupabaseAdapter } from "@auth/supabase-adapter"

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: SupabaseAdapter({
    url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
    secret: process.env.SUPABASE_SERVICE_ROLE_KEY!,
  }),
})
```

The Supabase adapter uses the service_role key to read/write sessions. If the key is empty at build time, `npm run build` will fail on the `/api/auth/[...nextauth]` route — use a placeholder in `.env.local` for local dev, real secret in `.env.production` for deployment.

## Middleware Caveats

Next.js 16 deprecated `middleware.ts` in favor of `proxy.ts` at the project root level. The old `middleware.ts` still works but emits a deprecation notice. Both export `{ auth as middleware }` the same way.

```typescript
// src/middleware.ts  — still works, deprecation warning
export { auth as middleware } from "@/lib/auth"
export const config = {
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
}
```

## Routing: Slugs Containing Slashes

Next.js `[slug]` route params only capture a single path segment. `encodeURIComponent()` does NOT work for slugs containing `/` because Next.js does NOT decode `%2F` back to `/` in route params.

**If slugs in your database contain slashes** (e.g. `karo/prd/03_Karo_PRD`), use a **catch-all `[...slug]`** route instead:

```
// Before (broken with slashes):
src/app/prds/[slug]/page.tsx       → URL: /prds/karo%2Fprd%2F03_Karo_PRD → slug = "karo%2Fprd%2F03_Karo_PRD" (NOT decoded)

// After (works):
src/app/prds/[...slug]/page.tsx    → URL: /prds/karo/prd/03_Karo_PRD     → slug = ["karo", "prd", "03_Karo_PRD"]
```

Join the array back to query the database:
```typescript
export default async function Page({ params }: { params: Promise<{ slug: string[] }> }) {
  const segments = (await params).slug
  const slug = Array.isArray(segments) ? segments.join("/") : segments
  // Now `slug` = "karo/prd/03_Karo_PRD" — use in Supabase .eq("slug", slug)
}
```

**Link generation:** With catch-all routes, just use the raw slug value — don't encode it:
```tsx
<Link href={`/prds/${prd.slug}`}>  {/* slug = "karo/prd/03_Karo_PRD" → path /prds/karo/prd/03_Karo_PRD */}
```

For entity types whose slugs DON'T contain slashes (e.g. product tracks, sprints by name), keep `[slug]`.

## Supabase Relationships: Silent Query Failure

Embedded relationship queries in Supabase fail **silently for the entire query** when the relationship name doesn't exist in the schema:

```typescript
// ❌ BROKEN — prd_epics_count doesn't exist as a named relationship
const { data } = await supabase
  .from("prds")
  .select("*, epics:prd_epics_count(count)")  // returns null for entire query!
```

The error is swallowed — `data` is `null` but no error is thrown. This causes list pages to show "No items" instead of data.

**Fix:** Always use separate queries for counts or aggregations instead of embedded relationship syntax:

```typescript
// ✅ WORKS — separate query
const { data: items } = await supabase.from("prds").select("*")

// Get counts in a separate query
const { data: counts } = await supabase.from("epics").select("prd_id")

const countMap: Record<number, number> = {}
for (const ep of counts ?? []) {
  countMap[ep.prd_id] = (countMap[ep.prd_id] ?? 0) + 1
}

const results = (items ?? []).map((item: any) => ({
  ...item,
  epicCount: countMap[item.id] ?? 0,
}))
```

**Quick check for existing broken relationships:**
```sql
-- Check if relationship names actually exist
SELECT * FROM information_schema.table_constraints 
WHERE constraint_name LIKE '%_fkey' AND table_name IN ('prds', 'epics', 'tasks');
```

Then search the codebase for `select("*,")` patterns with colon syntax like `relation_name:count` — those are likely broken.

## Restarting Next.js in WSL: Kill by PID, Not pkill

When restarting a Next.js server in WSL, `pkill -f "next start"` kills only the bash/npm wrapper processes — the actual `next-server` Node child **survives** and keeps serving the old build.

**Always kill by PID:**
```bash
# Find and kill ALL next + proxy processes
ps aux | grep -E 'next|serve-https' | grep -v grep | awk '{print $2}' | xargs kill -9

# Verify nothing remains
ps aux | grep -E 'next|serve-https' | grep -v grep
# → should return empty / 0

# Then start fresh
npx next start -p 3000 &
```

The same applies to the HTTPS proxy (`serve-https.js`) — kill by PID.

## WSL Networking: HTTPS Proxy Target

When running an HTTPS proxy in WSL that forwards to a Next.js server, use `127.0.0.1` as the target, NOT the WSL guest IP (e.g. `10.0.2.x`). Next.js binds to `localhost` by default, so the guest IP doesn't work for forwarding.

```javascript
// serve-https.js
const TARGET_HOST = '127.0.0.1';  // ✅ Not '10.0.2.4'
const TARGET_PORT = 3000;
```

To check Windows port forwarding rules (e.g. 443 → WSL 8443):
```bash
powershell.exe -Command "netsh interface portproxy show all"
```

## Theme: Forcing Light Mode

If the dashboard theme uses `@media (prefers-color-scheme: dark)` in `globals.css`, users with OS-level dark mode enabled will see a black background regardless of the light theme. To force light mode:

```css
/* Remove this entire block from globals.css: */
@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
  }
}
```

The default `:root { --background: #ffffff; }` then applies universally.

## Multi-Value Text Fields: Assignee/Owner with Comma-Separated Names

When a field like `assignee` or `owner` stores multiple names as comma-separated strings (e.g. `"Ali Hamza, Myat Thiha"`), filtering needs `ilike` instead of `eq`:

### Server-side (API route)

```typescript
// ❌ BROKEN — eq won't match "Ali Hamza, Myat Thiha" when filtering by "Ali Hamza"
if (assignee) query = query.eq("assignee", assignee)

// ✅ WORKS — ilike matches substring within comma-separated values
if (assignee) query = query.ilike("assignee", `%${assignee}%`)
```

### Client-side (filter in useMemo)

```typescript
// ❌ BROKEN — strict equality
if (assignee && t.assignee !== assignee) return false

// ✅ WORKS — substring match (handles null assignee gracefully)
if (assignee && t.assignee && !t.assignee.toLowerCase().includes(assignee.toLowerCase())) return false
```

### Canonical Name List and Data Cleanup

Use a canonical staff list (hardcoded in both server and client) to ensure filter dropdowns show clean names, not raw DB aliases. A one-time cleanup script normalizes existing data:

```javascript
// Name aliases → canonical
const ALIAS_MAP = {
  'Elaf Abdullah Saleh Alhaddad': 'Elaf Alhaddad',
  'Hamza': 'Ali Hamza',
};

function normalizeNames(value) {
  if (!value) return value;
  return value.split(',').map(s => {
    const trimmed = s.trim();
    return ALIAS_MAP[trimmed] || trimmed;
  }).join(', ');
}
```

**Filter option generation** — derive assignee options from canonical names that actually appear in the data, not raw DB distinct values:

```typescript
const staffLower = STAFF_NAMES.map((name) => ({ name, lower: name.toLowerCase() }))
const assigneeSet = new Set<string>()
for (const raw of rawAssignees) {
  const parts = raw.split(",").map((s) => s.trim())
  for (const part of parts) {
    const match = staffLower.find((s) => s.lower === part.toLowerCase())
    if (match) assigneeSet.add(match.name)
  }
}
const assignees = [...assigneeSet].sort()
```

### StaffPicker Component

Reusable multi-select component with search, pills, and comma-separated output:

```tsx
<StaffPicker
  value={form.assignee}       // "Ali Hamza, Myat Thiha"
  onChange={(v) => setForm({ ...form, assignee: v })}
  max={10}                     // max assignees
/>
```

The component auto-completes from a hardcoded canonical 40-name list. Output is always comma-separated canonical names — ready for storage.

### Displaying multi-value assignees

```tsx
const names = task.assignee
  ? task.assignee.split(",").map(s => s.trim()).filter(Boolean)
  : []

{names.length > 0 ? names.map(name => (
  <span key={name} className="inline-flex items-center rounded-full bg-navy px-2.5 py-0.5 text-xs font-semibold text-white">
    {name}
  </span>
)) : <span className="text-text-light">—</span>}
```

## Group By Toggle Pattern

Simple button-group toggle for switching grouping dimension on list pages (e.g. Epics grouped by Status vs Track):

```tsx
const [groupBy, setGroupBy] = useState<"status" | "track">("status")

// Toggle UI
<div className="flex items-center rounded-brand border border-grey-mid bg-white overflow-hidden">
  <button
    onClick={() => setGroupBy("status")}
    className={`px-3 py-1.5 text-xs font-semibold ${
      groupBy === "status" ? "bg-navy text-white" : "text-navy hover:bg-grey-light"
    }`}
  >
    Status
  </button>
  <button
    onClick={() => setGroupBy("track")}
    className={`px-3 py-1.5 text-xs font-semibold ${
      groupBy === "track" ? "bg-navy text-white" : "text-navy hover:bg-grey-light"
    }`}
  >
    Track
  </button>
</div>

// Grouping logic
for (const item of filtered) {
  const key = groupBy === "track"
    ? (item.product_tracks?.name ?? "Uncategorized")
    : (item.status ?? "Uncategorized")
  if (!grouped[key]) grouped[key] = []
  grouped[key].push(item)
}

// Custom sort order per grouping dimension
const trackOrder = ["v2", "v2 lite", "v1.5", "v1", "others"]
sortedGroups.sort(([a], [b]) => {
  const aIdx = trackOrder.indexOf(a)
  const bIdx = trackOrder.indexOf(b)
  if (aIdx === -1 && bIdx === -1) return a.localeCompare(b)
  if (aIdx === -1) return 1
  if (bIdx === -1) return -1
  return aIdx - bIdx
})
```

## Adding HTTP Methods to Existing Next.js Route Handlers

When adding a new method (e.g. `DELETE`) to a route file that already has `PATCH`:

```typescript
// src/app/api/tasks/[id]/route.ts

export async function PATCH(request, { params }) { /* existing */ }

// ✅ Just export another function — Next.js picks up all exported HTTP verbs
export async function DELETE(_request, { params }) {
  const { id } = await params
  const supabase = await createServerSupabaseClient()

  const { error } = await supabase.from("tasks").delete().eq("id", id)
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ success: true })
}
```

No special config needed — Next.js route handlers auto-detect exported function names as HTTP methods. A clean rebuild (`rm -rf .next && npm run build`) ensures the new export is picked up (turbopack sometimes caches stale route manifests).

**Auth note:** Testing DELETE via curl from localhost/CLI returns 405 because NextAuth middleware requires an authenticated session. The method works correctly when called from the browser with a valid session cookie — test in the UI after deploy.
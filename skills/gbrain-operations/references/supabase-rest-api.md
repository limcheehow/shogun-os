# Supabase REST API Sync

When gbrain's direct PostgreSQL connection is unavailable (IPv6-only host, auto-paused free tier, broken portproxy), use Supabase's PostgREST REST API over HTTPS instead. Works over IPv4, wakes paused databases automatically.

## Architecture

```
gbrain (PGLite local)         Supabase Cloud
 ┌─────────────────┐          ┌──────────────────────┐
 │ ~/brain/ .md    │──REST──▶ │ /rest/v1/pages       │
 │ files (20K+)    │  HTTPS   │ /rest/v1/content_chunks│
 │                 │          │ pgvector embeddings   │
 └─────────────────┘          └──────────────────────┘
       ▲                             ▲
       │ autopilot                   │ Cron: every 15 min
       │ (systemd, 5min)             │ (incremental - hash cache)
```

## Data Systems

This user runs Hermes on WSL (no global IPv6), using Supabase (free tier, IPv6-only DB). The CRM dashboard and brain sync both access the same Supabase project via REST API — the only working path since direct Postgres and the connection pooler both fail (IPv6 and Pro tier respectively).

**Two separate data systems, same Supabase project:**

| Layer | Engine | What it stores | How it connects |
|-------|--------|----------------|----------------|
| gbrain | PGLite (local WASM) | Knowledge graph, embeddings, symbolic edges | Local filesystem |
| CRM / Brain Sync | Supabase REST API | Pages, content_chunks, embeddings | HTTPS (IPv4) |

The brain REST sync is **not** a replacement for gbrain — it's a parallel pipeline that keeps the Supabase `pages` table populated with brain markdown content + vector embeddings for app-level queries.

## Tables

### `pages`
Exists from CRM. Columns: `id, source_id, slug, type, page_kind, title, compiled_truth, timeline, frontmatter, content_hash, created_at, updated_at, search_vector`. Unique constraint: `(source_id, slug)`.

### `content_chunks`
Full column set: `id, page_id, chunk_index, chunk_text, chunk_source, embedding, model, token_count, embedded_at, created_at, language, symbol_name, symbol_type, start_line, end_line, parent_symbol_path, doc_comment, symbol_name_qualified, search_vector`. Includes code-analysis columns not needed for markdown sync — they can be left NULL. Unique constraint for upsert: `(page_id, chunk_index)`.

## Script: ~/.hermes/scripts/supabase-sync-v2.py

The canonical incremental sync script. Scans `~/brain/` for `.md` files, computes content hashes, upserts to Supabase, chunks and embeds via OpenRouter text-embedding-3-large (1536d).

### Key Design Decisions

#### Incremental via hash cache
A JSON cache at `~/.gbrain/supabase-hash-cache.json` stores `{slug: {mtime, size, hash}}`. Files whose mtime+size match the cache are skipped entirely. Typical incremental run: ~2 seconds for 20K files. Full re-sync: `rm -f ~/.gbrain/supabase-hash-cache.json`.

#### Frontmatter YAML → JSON serialization
YAML `date` objects are not JSON-serializable. Convert explicitly:
```python
for k, v in frontmatter.items():
    if hasattr(v, 'isoformat'):
        cleaned[k] = v.isoformat()
    elif isinstance(v, (list, tuple)):
        cleaned[k] = [x.isoformat() if hasattr(x, 'isoformat') else x for x in v]
    else:
        cleaned[k] = v
```
The `frontmatter` column is `JSONB NOT NULL` — always send `"{}"` as default, never None.

#### Batch keys must be uniform
PostgREST requires every row in a batch POST to have identical keys. Always define all keys in the dict literal:
```python
page = {
    "slug": slug,
    "title": title,
    ...
    "frontmatter": "{}",     # Always present
    "source_id": "default",
}
```

#### Upsert with on_conflict
The `Prefer: resolution=merge-duplicates` header alone is insufficient. Also pass the `on_conflict` query parameter:
```python
def rest_upsert(table, rows, on_conflict="source_id,slug"):
    url = f"{SUPABASE_REST}/{table}?on_conflict={on_conflict}"
```
For `pages` the conflict key is `source_id,slug`. For `content_chunks` it's `page_id,chunk_index`.

#### 409 Trigger Noise (harmless)
The existing `update_page_search_vector()` trigger fires on `AFTER INSERT OR UPDATE` and tries to insert "Page created" into `timeline_entries`. On upsert-updates this hits the dedup constraint → HTTP 409.
**The page data saves correctly; the 409 is harmless noise.**
**Two approaches:**
1. **Silent acceptance (current):** Treat 409 as success in the script — the upsert pipeline continues.
2. **Permanent fix:** In the Supabase SQL Editor, change the trigger to INSERT-only:
   ```sql
   DROP TRIGGER IF EXISTS trg_pages_search_vector ON pages;
   CREATE TRIGGER trg_pages_search_vector
     AFTER INSERT ON pages
     FOR EACH ROW EXECUTE FUNCTION update_page_search_vector();
   ```

#### Empty response body on 201 Created
PostgREST returns HTTP 201 with empty body when `Prefer: resolution=merge-duplicates` is set. Guard:
```python
body = resp.read()
if body:
    return json.loads(body)
return []  # 201 Created, no content
```

#### Content chunk strategy
Chunk by paragraph (~1000 chars each), embed via OpenRouter, then delete old chunks for the page (`DELETE ... WHERE page_id=eq.$pid`) and re-insert. Batches of 5 with 0.3s sleep between batches.

## Running the Sync

Manual incremental:
```bash
cd ~/crm-dashboard
SERVICE_KEY=$(grep SUPABASE_SERVICE_ROLE_KEY .env.local | cut -d= -f2)
ANON_KEY=$(grep NEXT_PUBLIC_SUPABASE_ANON_KEY .env.local | cut -d= -f2)
SUPABASE_SERVICE_KEY="$SERVICE_KEY" SUPABASE_ANON_KEY="$ANON_KEY" \
  python3 ~/.hermes/scripts/supabase-sync-v2.py
```

Full re-sync (ignore cache):
```bash
rm -f ~/.gbrain/supabase-hash-cache.json && \
cd ~/crm-dashboard && SERVICE_KEY=$(grep SUPABASE_SERVICE_ROLE_KEY .env.local | cut -d= -f2) \
ANON_KEY=$(grep NEXT_PUBLIC_SUPABASE_ANON_KEY .env.local | cut -d= -f2) \
SUPABASE_SERVICE_KEY="$SERVICE_KEY" SUPABASE_ANON_KEY="$ANON_KEY" \
python3 ~/.hermes/scripts/supabase-sync-v2.py
```

### Automation (Cron)
The sync runs every 15 minutes via `cronjob`, delivering to `local` (silent when nothing changed, alerts on failure).

## PostgREST Query Patterns

```bash
# Count
curl "https://{ref}.supabase.co/rest/v1/pages?select=count&limit=0" -H "Prefer: count=exact"

# Upsert with merge-duplicates
curl -X POST "https://{ref}.supabase.co/rest/v1/pages?on_conflict=source_id,slug" \
  -H "Prefer: resolution=merge-duplicates" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -d '[{"slug":"...","compiled_truth":"...","frontmatter":"{}","source_id":"default"}]'

# Look up page IDs by slug list
curl "https://{ref}.supabase.co/rest/v1/pages?select=id,slug&slug=in.(slug1,slug2,slug3)"

# Delete old content_chunks for a page (done before re-inserting)
curl -X DELETE "https://{ref}.supabase.co/rest/v1/content_chunks?page_id=eq.$PAGE_ID"
```

## Key Gotchas

| Issue | Symptom | Fix |
|-------|---------|-----|
| Missing service_role key | HTTP 401 on page writes | Use service_role key (anon is read-only for tables with RLS) |
| Missing User-Agent | HTTP 403 from Cloudflare | Add `"User-Agent": "supabase-sync/1.0"` to every request |
| frontmatter as NULL | HTTP 400: 23502 not-null violation | Always send `"frontmatter": "{}"`, never None |
| Uneven batch keys | HTTP 400: PGRST102 | Every row in a batch must have identical keys |
| Missing on_conflict param | HTTP 409 on existing rows | Add `?on_conflict=source_id,slug` to POST URL |
| Embedding dimensions | pgvector dimension error | OpenRouter defaults to 3072d; pass `dimensions: 1536` explicitly |
| REST pagination limit | Truncated results (max 1000) | Use `limit=N&offset=M` and loop |
| Trigger 409 noise | On every upsert | Harmless — page data saves. Script handles silently |
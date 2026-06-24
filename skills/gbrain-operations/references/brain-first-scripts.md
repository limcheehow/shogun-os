# Brain-First Lookup & Signal Capture Scripts

Three companion scripts that work around PGLite's exclusive lock by using
the Supabase REST API (always available) and the filesystem (no lock needed).

## brain-query.sh — Brain-first lookup via Supabase REST

```bash
~/.hermes/scripts/brain-query.sh "search term" [limit]
```

Reads Supabase credentials from `~/crm-dashboard/.env.local`, URL-encodes the
query, and hits the Supabase REST API (`/rest/v1/pages`) with ILIKE filters on
slug and title. Returns JSON: `[{slug, title, updated_at}]`.

**Always available** — no PGLite lock contention. Use for every person/company
lookup before falling back to external APIs.

**Known limitation:** Text search is ILIKE-based (not vector/FTS). Misses pages
where the query term appears in the page body but not in the slug or title.

## brain-capture.sh — Signal capture via filesystem

```bash
~/.hermes/scripts/brain-capture.sh "Title" "Content" [folder]
```

Writes a markdown page directly to `~/brain/<folder>/`. Default folder: `inbox`.
No lock contention because it only touches the filesystem. gbrain autopilot picks
up new files on its next cycle (usually within 2 min). Supabase REST sync picks
them up within 15 min.

**Use for:** Capturing original ideas, entity mentions, signal detection results.

## brain-think.sh — gbrain think with autopilot pause

```bash
~/.hermes/scripts/brain-think.sh "question" [--save]
```

Pauses autopilot, runs `gbrain think`, restarts autopilot. Use for deep multi-hop
synthesis across 27K pages. Requires ~60-120s per question. The `--save` flag
persists the synthesis to `synthesis/<slug>` in the brain.

## Python wrapper (alternative for all commands)

For commands that need reliable API key injection (avoiding bash shell escaping):

```bash
python3 ~/.hermes/scripts/gbrain-runner.py <command> [args]
```

See `references/python-wrapper-pattern.md` for details.
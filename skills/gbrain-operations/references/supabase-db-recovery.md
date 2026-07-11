# Supabase DB Recovery

## Symptom Checklist

| Symptom | Likely Issue |
|---------|-------------|
| `password authentication failed for user "postgres"` | Config.json password corrupted to `***` |
| `write CONNECT_TIMEOUT` to 172.31.176.1:5432 | Portproxy forwarding but DB paused or dead |
| `connect ECONNREFUSED` to IPv6 address | IPv6-only host, no portproxy, WSL has no IPv6 route |
| `Could not connect to configured DB` | Any of the above, or config file wiped |

## Recovery Path A-Prime: Switch Back to Existing Supabase (PGLite Dead, Supabase Alive)

**Use this when:** PGLite has crashed with `Aborted()` but a Supabase project already has gbrain schema + data (check with `curl` to the REST API).

**Pre-flight check:** The Supabase REST API reveals existing tables and approximate page counts:
```bash
# Check if Supabase has gbrain tables (200 = yes, 404 = no project or wrong URL)
curl -s -o /dev/null -w "%{http_code}" "$SUPABASE_URL/rest/v1/pages?select=count&limit=1" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY"

# Check approximate page count
curl -s "$SUPABASE_URL/rest/v1/pages?select=count" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY"
# Returns e.g. [{"count":29818}]
```

**The gbrain `init` command will FAIL** when PGLite is dead — it auto-detects PGLite and tries `PGlite.create()`, crashing with `Aborted()`. **Do not use `gbrain init`.** Switch the config manually:

1. **Get the database connection string.** The Supabase connection string format is:
   ```
   postgresql://postgres.[PROJECT_REF]:PASSWORD@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
   - `PROJECT_REF` = the subdomain from `SUPABASE_URL` (e.g. `acfctcmxnfipihrdauxj`)
   - `PASSWORD` = the DB password (from Supabase Dashboard → Project Settings → Database)
   - `REGION` = from `SUPABASE_URL` (e.g. `ap-southeast-1`)

   **On WSL with IPv6-only Supabase**, use the pooler on port 6543 (it works over IPv4 via AWS's NAT). If port 6543 is blocked, use a Windows portproxy for port 5432 (see Recovery Path B below).

2. **Edit `~/.gbrain/config.json`:**
   ```bash
   cat > ~/.gbrain/config.json << 'EOF'
   {
     "engine": "postgres",
     "database_url": "postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres?sslmode=require",
     "embedding_model": "backup-provider:openai/text-embedding-3-small",
     "embedding_dimensions": 1536,
     "expansion_model": "openai:gpt-5.2",
     "chat_model": "openai:gpt-5.2"
   }
   EOF
   ```
   Replace `PROJECT_REF`, `PASSWORD`, and `REGION` with actual values.

3. **Verify:**
   ```bash
   cd ~/gbrain && bun run src/cli.ts doctor
   ```
   Should show `[OK] connection: Connected, NNN pages` (the count from the old data).

4. **Sync fresh data** (if brain files have changed since last sync):
   ```bash
   cd ~/gbrain && bun run src/cli.ts sync --repo ~/brain --skip-failed
   ```
   No `OPENROUTER_API_KEY` gymnastics needed — Postgres engine stores config in `database_url`.

5. **Re-embed** (likely needed if pages changed):
   ```bash
   cd ~/gbrain && bun run src/cli.ts embed --stale
   ```

6. **Re-install autopilot** (the systemd service still points at PGLite):
   ```bash
   gbrain autopilot --uninstall
   gbrain autopilot --install --repo ~/brain
   ```
   Then re-apply PATH hardening (see main skill).

**Key difference from `gbrain migrate`:** This is a manual config switch, not a migration. The data already lives in Supabase — we just point gbrain at it. No data is copied. Much faster than `migrate --to supabase` which exports from PGLite (which is dead anyway).

## Recovery Path A: Switch to PGLite (Fastest, No DB Needed)

The brain markdown files in `~/brain/` are the source of truth. PGLite is just the search index.

```bash
# 1. Switch config to PGLite
echo '{"engine": "pglite"}' > ~/.gbrain/config.json

# 2. Re-init (migrations auto-run)
cd ~/gbrain && bun run src/cli.ts init

# 3. Sync from filesystem
cd ~/gbrain && \
  OPENAI_API_KEY="$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-)" \
  OPENAI_BASE_URL="https://backup-provider.ai/api/v1" \
  bun run src/cli.ts sync --repo ~/brain

# 4. Embed
cd ~/gbrain && \
  OPENAI_API_KEY="$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-)" \
  OPENAI_BASE_URL="https://backup-provider.ai/api/v1" \
  bun run src/cli.ts embed --stale
```

Note: gbrain reads `OPENAI_API_KEY` + `OPENAI_BASE_URL` env vars. Since the OpenAI key is exhausted, set these to the Backup Provider key + base URL. There's no gbrain config for "embedding provider" — you must always inject env vars or use the permanent wrapper.

## Recovery Path B: Fix Supabase Connection

### Fix Corrupted Config.json

If `~/.gbrain/config.json` has `password: ***` instead of the real password:

1. **Recover password from Supabase dashboard:** Project Settings → Database → Database password (reset it if needed)
2. **Recover password from session history:** Run `session_search query="supabase database setup password"` (both cron and interactive sessions print the connection string)
3. **Rewrite config.json:**
```json
{
  "engine": "postgres",
  "database_url": "postgresql://postgres:REAL_PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres?sslmode=require"
}
```

### WSL IPv6/Portproxy — Supabase Free Tier Limitations

**Supabase free tier = IPv6-only DB**, pooler requires a Pro plan:
- `db.*.supabase.co:5432` — IPv6 only (AAAA record). WSL has only link-local `fe80::` — "Network is unreachable".
- `aws-0-*-*.pooler.supabase.com:6543` — IPv4 reachable, but free tier returns `FATAL: Tenant or user not found`. Pooler is a Pro-plan feature.
- No alternative username format (`postgres.acfctcmxnfipihrdauxj`, `acfctcmxnfipihrdauxj.postgres`, etc.) bypasses this check.

**Workarounds (none use Supabase directly from WSL):**

| Path | Works? | Why |
|------|--------|-----|
| Upgrade to Pro ($25/mo) | ✅ | Enables pooler on IPv4 |
| Local Postgres on WSL (apt install postgresql-16-pgvector) | ✅ | No cloud dep, no IPv6 issues |
| Portproxy (`netsh interface portproxy`) | ❌ | Forwards traffic to an IPv6 address WSL can't route to |
| REST API as gbrain engine | ❌ | gbrain needs pgvector, schema migrations, transactions |

```bash
# Check if host is IPv6-only
getent hosts db.PROJECT_REF.supabase.co
# IPv6 address only → free tier, no pooler access

# Check pooler connectivity (will say REACHABLE even on free tier)
timeout 5 bash -c 'echo > /dev/tcp/aws-0-us-east-1.pooler.supabase.com/6543 && echo "REACHABLE" || echo "UNREACHABLE"'

# Verify pooler is blocked for this project (free tier symptom)
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='aws-0-us-east-1.pooler.supabase.com', port=6543,
        user='postgres.$REF', password='***', dbname='postgres',
        connect_timeout=8, sslmode='require'
    )
except psycopg2.OperationalError as e:
    if 'Tenant or user not found' in str(e):
        print('Free tier — need Pro plan for pooler')
"
```

### Fix Autopilot After DB Switch

If switching between PGLite and Supabase, the autopilot systemd service may still reference the old engine. Re-install:
```bash
gbrain autopilot --uninstall
gbrain autopilot --install --repo ~/brain
# Then re-apply PATH hardening (see main skill)
```

## Healthy State Checklist

- `gbrain doctor` shows `[OK] connection: Connected, NNNN pages`
- `[OK] embeddings: NNN% coverage`
- `[OK] schema_version: 92 (latest: 92)`
- Autopilot: `Active: active (running)` via `systemctl --user status`
- Logs at `~/.gbrain/autopilot.log` show `[cycle] score=...`
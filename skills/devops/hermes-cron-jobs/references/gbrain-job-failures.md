# gbrain Cron Job Failure Patterns

Real failure patterns discovered during cron audits, with fixes applied.

## Pattern 1: Google OAuth Token Expiry → Migrate to SA-DWD

**Status:** ✅ Fixed (June 2026) — `google-api` migrated to SA-DWD
**Was:** The `google-api` bash script used `~/.gbrain/google-tokens.json` with OAuth refresh tokens that expired, causing `unauthorized_client`.
**Fix applied:** Rewrote `~/.local/bin/google-api` as Python, using Service Account key (`~/.hermes/service-account-key.json`) with Domain-Wide Delegation. Default impersonates `cheehow@example.com`. Uses the EXACT same SCOPES list as `google_api.py` — mismatched scopes cause the same `unauthorized_client` error.
**Affected jobs:** gbrain-email-collector, gbrain-calendar-collector, Collect Gmail to gbrain

## Pattern 2: /tmp File Volatility → Use Config YAML

**Status:** ✅ Fixed (June 2026) — `supabase-sync-v2.py` reads from `config.yaml`
**Was:** Script hardcoded `open("/tmp/openrouter_key.txt")` which disappears on reboot.
**Fix applied:** `get_client()` now reads `api_key` and `base_url` from `~/.hermes/config.yaml`'s `model` section. Switched embedding model to `text-embedding-v4` with `dimensions=1536` (DashScope supports this — no DB migration needed).
**Affected jobs:** supabase-product-sync

## Pattern 3: Lock Contention (Same Resource)

**Symptom:** `Another sync is in progress (lock gbrain-sync held)`
**Affected jobs:** gbrain-dream-cycle (2am) fails because gbrain-live-sync (every 15min) holds the `gbrain sync` lock.

Both scripts call `gbrain sync --repo ~/brain`:
- `gbrain-live-sync.sh`: `exec gbrain sync --repo ~/brain`
- `gbrain-dream-cycle.sh`: `gbrain sync --repo ~/brain` (as first step)

**Fix applied:** Added retry loop (5 attempts, 30s backoff) to dream-cycle. If all 5 fail, exits gracefully rather than silently dropping the entire maintenance cycle.
**Alternative fixes:** Offset dream-cycle schedule by 5 min (not possible via cronjob tool alone).

## Pattern 4: Daemon-in-Cron (Infinite Loop)

**Symptom:** `Script timed out after 120s`
**Affected jobs:** Signal Monitor Watchdog

**Root cause:** `gateway-signal-monitor.sh` was a `while true` daemon loop. Cron expects scripts to exit. Early runs "succeeded" only because a lockfile guard made them `exit 0` immediately.

**Fix applied:** Rewrote as one-shot check. Compares current gateway PID vs saved state. Reports only on death/restart. No output = cron scheduler treats as silent (correct behavior for a watchdog).

## Pattern 5: Agent Timeout on Long Scripts → Incremental

**Status:** ✅ Fixed (June 2026)
**Was:** Sync personal-brain to gbrain took 2 hours but agent had 300s turn timeout.
**Fix applied:** Converted `sync-personal-brain.sh` to incremental mode via `git diff` against last sync hash. First run is full import; subsequent runs are seconds. Also switched cron job to `no_agent=true` to avoid LLM turn timeout.

## Pattern 6: gbrain import on Accumulated Directories

**Symptom:** `gbrain import ~/brain/data/email --no-embed` times out at 120s, then 300s — scans 2,870+ files at ~2 files/second = 24+ minutes.
**Root cause:** The collector writes files to `~/brain/data/email/` but never cleans up. `gbrain import` processes ALL files even though 99% are already in the DB.
**Fix:** Use `--self-import` flag on `collect-gmail-team.py` — imports only the specific files just written (`gbrain import --no-embed <file1> <file2> ...`) instead of the entire directory. This is embedded in the parallel subagent architecture (see `gotapway-dwd` skill).

## Pattern 7: Session DB Corruption (Non-Fatal)

**Symptom:** Agent log shows `Session DB creation failed: database disk image is malformed`
**Impact:** Agent loses prefix cache for that turn (higher token cost, slower response). Does NOT crash the agent — it retries on the next turn. Related to Postgres migration — sessions moved to Postgres but the cron scheduler may still reference SQLite state.db.

## Diagnostic Commands

```bash
# List all failing jobs — cronjob tool action='list', filter last_status: error

# Read latest output for a job
ls -lt ~/.hermes/cron/output/<job_id>/ | head -3
cat ~/.hermes/cron/output/<job_id>/<latest.md>

# Test SA-DWD auth
python3 -c "
from google.oauth2 import service_account; import google.auth.transport.requests
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', ...]
creds = service_account.Credentials.from_service_account_file(
    '/home/tapway/.hermes/service-account-key.json', scopes=SCOPES,
    subject='cheehow@example.com')
creds.refresh(google.auth.transport.requests.Request())
print('Token OK:', creds.valid)
"

# Check gbrain import speed on accumulated directory
ls ~/brain/data/email/*.md | wc -l  # count files
timeout 10 gbrain import ~/brain/data/email --no-embed --dry-run 2>&1 | head -5

# Monitor cron agent progress
grep "cron_<job_id>" ~/.hermes/logs/agent.log | tail -10
# Key events: delegate_task completed, tool terminal returned error, Turn ended
```
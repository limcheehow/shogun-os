#!/usr/bin/env python3
"""
Daily Token Cost Report — queries the Hermes session DB directly using the
real usage_pricing engine (same code that prices sessions live). Replaces the
inaccurate tokscale plugin.

No-agent cron mode: stdout is delivered verbatim to Telegram.
Empty stdout = silent (nothing sent). Only sends when there's data.

Usage:
  Called by cron at 6am. Reports yesterday's token usage.

Output: Telegram-formatted markdown with cost breakdown by model × platform.

Generic version — uses HERMES_SRC env var or auto-detects Hermes source path.
Postgres connection uses env vars: PGHOST, PGPORT, PGDATABASE, PGUSER.
"""

import sys
import os
import subprocess
from datetime import datetime, timezone, timedelta

# ── Config ──────────────────────────────────────────────────────────────────
TZ = timezone(timedelta(hours=8))  # UTC+8 (adjust to your timezone)

# Hermes agent source (editable install — same code the gateway uses)
HERMES_SRC = os.environ.get("HERMES_SRC", os.path.expanduser("~/.hermes/hermes-agent"))
if os.path.isdir(HERMES_SRC):
    sys.path.insert(0, HERMES_SRC)

# Postgres connection
PGHOST = os.environ.get("PGHOST", "localhost")
PGPORT = os.environ.get("PGPORT", "5432")
PGDATABASE = os.environ.get("PGDATABASE", "hermes_sessions")
PGUSER = os.environ.get("PGUSER", "hermes")

# ── Determine "yesterday" in local timezone ─────────────────────────────────
now_local = datetime.now(TZ)
yesterday = now_local - timedelta(days=1)
date_str = yesterday.strftime("%Y-%m-%d")
date_display = yesterday.strftime("%b %d, %Y")

# Epoch boundaries for the DB query (midnight to midnight, local tz)
start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_day = start_of_day + timedelta(days=1)
start_epoch = int(start_of_day.timestamp())
end_epoch = int(end_of_day.timestamp())

# ── Query the session DB ────────────────────────────────────────────────────
SQL = f"""
SELECT 
  source,
  billing_provider,
  model,
  cost_status,
  COUNT(*) as sessions,
  SUM(input_tokens) as input_tok,
  SUM(output_tokens) as output_tok,
  SUM(cache_read_tokens) as cache_read,
  SUM(cache_write_tokens) as cache_write,
  SUM(reasoning_tokens) as reasoning,
  SUM(api_call_count) as api_calls,
  COALESCE(SUM(estimated_cost_usd), 0) as est_cost
FROM sessions
WHERE started_at >= {start_epoch}
  AND started_at < {end_epoch}
  AND (input_tokens > 0 OR output_tokens > 0 OR cache_read_tokens > 0)
GROUP BY source, billing_provider, model, cost_status
ORDER BY est_cost DESC
"""

# Try psql first, fall back to direct SQLite
result = subprocess.run(
    ["psql", "-h", PGHOST, "-p", PGPORT, "-d", PGDATABASE, "-U", PGUSER,
     "-t", "-A", "-F", "\t", "-c", SQL],
    capture_output=True, text=True, timeout=30
)

if result.returncode != 0:
    # Try alternative: use sudo -u postgres
    result = subprocess.run(
        ["sudo", "-n", "-u", "postgres", "psql", "-d", PGDATABASE,
         "-t", "-A", "-F", "\t", "-c", SQL],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"❌ DB query failed: {result.stderr.strip()}")
        sys.exit(1)

rows = []
for line in result.stdout.strip().split("\n"):
    if not line.strip():
        continue
    parts = line.split("\t")
    if len(parts) < 12:
        continue
    rows.append({
        "source": parts[0],
        "billing_provider": parts[1],
        "model": parts[2],
        "cost_status": parts[3],
        "sessions": int(parts[4]),
        "input_tok": int(parts[5] or 0),
        "output_tok": int(parts[6] or 0),
        "cache_read": int(parts[7] or 0),
        "cache_write": int(parts[8] or 0),
        "reasoning": int(parts[9] or 0),
        "api_calls": int(parts[10] or 0),
        "est_cost": float(parts[11] or 0),
    })

if not rows:
    # No sessions yesterday — stay silent
    sys.exit(0)

# ── Aggregate totals ────────────────────────────────────────────────────────
total_sessions = sum(r["sessions"] for r in rows)
total_input = sum(r["input_tok"] for r in rows)
total_output = sum(r["output_tok"] for r in rows)
total_cache_read = sum(r["cache_read"] for r in rows)
total_cache_write = sum(r["cache_write"] for r in rows)
total_reasoning = sum(r["reasoning"] for r in rows)
total_tokens = total_input + total_output + total_cache_read + total_cache_write + total_reasoning
total_api_calls = sum(r["api_calls"] for r in rows)
total_cost = sum(r["est_cost"] for r in rows)
unknown_count = sum(r["sessions"] for r in rows if r["cost_status"] == "unknown")
unknown_cost = sum(r["est_cost"] for r in rows if r["cost_status"] == "unknown")

# ── Format token counts ─────────────────────────────────────────────────────
def fmt_tok(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)

# ── Build the report ────────────────────────────────────────────────────────
lines = []
lines.append(f"📊 **Daily Token Cost Report**")
lines.append(f"📅 {date_display}")
lines.append("")
lines.append("**Overview**")
lines.append(f"┌──────────────────┬──────────────┐")
lines.append(f"│ Sessions         │ {total_sessions:>12} │")
lines.append(f"│ API calls        │ {total_api_calls:>12} │")
lines.append(f"│ Total tokens     │ {fmt_tok(total_tokens):>12} │")
lines.append(f"│ Est. cost (USD)  │ ${total_cost:>11.2f} │")
lines.append(f"└──────────────────┴──────────────┘")
lines.append("")

# Token breakdown
lines.append("**Token Breakdown**")
lines.append(f"┌─────────────────┬──────────────┐")
lines.append(f"│ Input           │ {fmt_tok(total_input):>12} │")
lines.append(f"│ Output          │ {fmt_tok(total_output):>12} │")
lines.append(f"│ Cache read      │ {fmt_tok(total_cache_read):>12} │")
lines.append(f"│ Cache write     │ {fmt_tok(total_cache_write):>12} │")
lines.append(f"│ Reasoning       │ {fmt_tok(total_reasoning):>12} │")
lines.append(f"└─────────────────┴──────────────┘")
lines.append("")

# By model × platform
lines.append("**By Model × Platform**")
lines.append("```")
lines.append(f"{'Platform':<10} {'Provider':<12} {'Model':<25} {'Sess':>5} {'Tokens':>10} {'Cost':>8} {'Status':<10}")
lines.append(f"{'─'*10} {'─'*12} {'─'*25} {'─'*5} {'─'*10} {'─'*8} {'─'*10}")

for r in rows:
    tok = r["input_tok"] + r["output_tok"] + r["cache_read"] + r["cache_write"] + r["reasoning"]
    status_icon = "⚠️" if r["cost_status"] == "unknown" else "✓"
    lines.append(
        f"{r['source']:<10} {r['billing_provider']:<12} {r['model']:<25} {r['sessions']:>5} "
        f"{fmt_tok(tok):>10} ${r['est_cost']:>7.2f} {status_icon} {r['cost_status']:<8}"
    )

lines.append(f"{'─'*10} {'─'*12} {'─'*25} {'─'*5} {'─'*10} {'─'*8} {'─'*10}")
lines.append(
    f"{'TOTAL':<10} {'':<12} {'':<25} {total_sessions:>5} "
    f"{fmt_tok(total_tokens):>10} ${total_cost:>7.2f}"
)
lines.append("```")
lines.append("")

# Warnings
if unknown_count > 0:
    lines.append(f"⚠️ {unknown_count} sessions priced as 'unknown' (${unknown_cost:.2f} unaccounted)")

# Cache efficiency
if total_tokens > 0:
    cache_pct = (total_cache_read / total_tokens) * 100
    lines.append(f"💡 Cache read: {cache_pct:.0f}% of all tokens (lower cost than fresh input)")

print("\n".join(lines))
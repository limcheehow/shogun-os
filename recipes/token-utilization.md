---
id: token-utilization
name: Token Utilization Monitoring
version: 1.0.0
description: Daily token usage and cost report via Tokscale. Tracks AI spend across all Hermes profiles, per-model breakdown, cache efficiency, and month-over-month trends.
category: monitor
requires: []
secrets: []
health_checks:
  - type: script
    command: "tokscale --json --month --no-spinner 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f\"TOKSCALE_OK month={d[\"entries\"][0][\"month\"]} cost=${d[\"totalCost\"]:.2f}\")' 2>/dev/null || echo 'TOKSCALE_FAIL'"
    label: "Tokscale reporting"
setup_time: 5 min
cost_estimate: "$0 (Tokscale is free)"
---

# Token Utilization Monitoring

Daily AI spend tracking across all Hermes profiles. Catch cost anomalies early, compare model efficiency, track cache hit ratios, and build a habit of awareness.

## IMPORTANT: Instructions for the Agent

**You are the installer.** Tokscale is already installed and wired to track all Hermes profiles. This recipe adds a daily cron job that generates a human-readable token utilization report.

## Architecture

```
Tokscale (reads all Hermes state.db files)
  ↓
Daily cron (default profile)
  ↓ no_agent script
Script runs: tokscale monthly --json + tokscale models --json --today
  ↓
Formatted report delivered to user
```

## Prerequisites

- Tokscale installed: `~/.npm-global/bin/tokscale` (v3.1.2)
- All Hermes profiles tracked in `~/.config/tokscale` (already configured)

## Current Baseline

| Metric | May 2026 | June 2026 (so far) |
|--------|----------|-------------------|
| Input tokens | 432M | 409M |
| Output tokens | 12.7M | 8.4M |
| Cache reads | 1.97B | 1.23B |
| Messages | 44,362 | 39,170 |
| **Total cost** | **$93.65** | **$51.74** |
| **Cumulative** | | **$145.39** |

## Setup Flow

### Step 1: Test Tokscale Report

```bash
# Quick check — monthly summary
tokscale monthly --json --no-spinner

# Model breakdown for today
tokscale models --json --today --no-spinner

# Models for this month
tokscale models --json --month --no-spinner
```

**STOP until both commands return valid JSON with actual data.**

### Step 2: Create the Watchdog Script

Write to `~/.hermes/scripts/token-util-report.sh`:

```bash
#!/bin/bash
# Token Utilization Report
# Generates a daily AI spend summary using Tokscale
# Runs as no_agent=true cron — output is delivered verbatim

TOKSCALE="$HOME/.npm-global/bin/tokscale"
TODAY=$(date +%Y-%m-%d)

# Monthly summary (this month + last month)
MONTHLY=$($TOKSCALE monthly --json --no-spinner 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$MONTHLY" ]; then
  echo "TOKSCALE_ERROR: monthly report failed"
  exit 1
fi

# Today's model breakdown
TODAY_MODELS=$($TOKSCALE models --json --today --no-spinner 2>/dev/null)

# This month's model breakdown
MONTH_MODELS=$($TOKSCALE models --json --month --no-spinner 2>/dev/null)

python3 << PYEOF
import json, sys, os

monthly = json.loads(os.environ.get('MONTHLY', '{}'))
today_models = json.loads(os.environ.get('TODAY_MODELS', '{}'))
month_models = json.loads(os.environ.get('MONTH_MODELS', '{}'))

today = "$TODAY"

entries = monthly.get('entries', [])
total_cost = monthly.get('totalCost', 0)

# ── Header ──
lines = [f"# 🤖 Token Utilization — {today}", ""]

# ── Monthly Summary ──
lines.append("## 📊 Monthly Summary")
lines.append("")
lines.append("| Month | Input Tokens | Output Tokens | Cache Reads | Messages | Cost |")
lines.append("|-------|-------------|--------------|-------------|----------|------|")

for e in entries:
    inp = f"{e['input']:,}" if e['input'] > 0 else "—"
    out = f"{e['output']:,}" if e['output'] > 0 else "—"
    cache = f"{e.get('cacheRead', 0):,}" if e.get('cacheRead', 0) > 0 else "—"
    msgs = f"{e['messageCount']:,}" if e['messageCount'] > 0 else "—"
    cost = f"${e['cost']:.2f}"
    lines.append(f"| {e['month']} | {inp} | {out} | {cache} | {msgs} | {cost} |")

lines.append(f"| **Total** | | | | | **\${total_cost:.2f}** |")
lines.append("")

# ── This Month by Model ──
m_entries = month_models.get('entries', [])
if m_entries:
    lines.append("## 🧠 This Month — Per Model")
    lines.append("")
    lines.append("| Client | Model | Input | Output | Cache Read | Messages | Cost |")
    lines.append("|--------|-------|-------|--------|------------|----------|------|")
    for e in m_entries:
        inp = f"{e['input']:,}" if e['input'] > 0 else "—"
        out = f"{e['output']:,}" if e['output'] > 0 else "—"
        cache = f"{e.get('cacheRead', 0):,}" if e.get('cacheRead', 0) > 0 else "—"
        msgs = f"{e['messageCount']:,}" if e['messageCount'] > 0 else "—"
        cost = f"${e['cost']:.2f}"
        model_short = e['model'].split('/')[-1] if '/' in e['model'] else e['model']
        lines.append(f"| {e['client']} | {model_short} | {inp} | {out} | {cache} | {msgs} | {cost} |")
    lines.append("")

# ── Today's Activity ──
t_entries = today_models.get('entries', [])
if t_entries:
    t_total = sum(e.get('cost', 0) for e in t_entries)
    t_msgs = sum(e.get('messageCount', 0) for e in t_entries)
    lines.append(f"## ⚡ Today ({today})")
    lines.append("")
    lines.append(f"**{t_msgs} messages** — **\${t_total:.2f}**")
    lines.append("")
    lines.append("| Model | Messages | Cost |")
    lines.append("|-------|----------|------|")
    for e in t_entries:
        msgs = f"{e['messageCount']:,}"
        cost = f"${e['cost']:.2f}"
        model_short = e['model'].split('/')[-1] if '/' in e['model'] else e['model']
        lines.append(f"| {model_short} | {msgs} | {cost} |")
    lines.append("")

# ── Alerts ──
if len(entries) >= 2:
    prev_cost = entries[0]['cost'] if entries[0]['cost'] > 0 else 0.01
    curr = next((e for e in entries if e['month'] != entries[0]['month']), None)
    if curr and prev_cost > 0:
        days_ratio = 1.0  # full month comparison
        # Simple projection: if current month's cost / days elapsed extrapolates higher
        lines.append("## 🚨 Observations")
        lines.append("")
        # Check for unusual spikes
        for e in month_models.get('entries', []):
            if e['cost'] > 20:
                model_short = e['model'].split('/')[-1] if '/' in e['model'] else e['model']
                lines.append(f"- ⚠️ High spend on **{model_short}**: \${e['cost']:.2f} this month")
        lines.append("")

print("\n".join(lines))
PYEOF
```

Make it executable:
```bash
chmod +x ~/.hermes/scripts/token-util-report.sh
```

### Step 3: Verify the Script

```bash
MONTHLY="$(tokscale monthly --json --no-spinner 2>/dev/null)" \
TODAY_MODELS="$(tokscale models --json --today --no-spinner 2>/dev/null)" \
MONTH_MODELS="$(tokscale models --json --month --no-spinner 2>/dev/null)" \
~/.hermes/scripts/token-util-report.sh
```

Should output a formatted markdown table with cost data.

### Step 4: Create the Cron Job

In the **default** profile (shared infrastructure — tracks ALL Hermes profiles):

```bash
hermes cron create \
  --name "Token Utilization Report" \
  --schedule "0 8 * * 1" \
  --script token-util-report.sh \
  --no-agent \
  --deliver origin
```

| Parameter | Value | Why |
|-----------|-------|-----|
| `--script` | `token-util-report.sh` | Path relative to `~/.hermes/scripts/` |
| `--no-agent` | true | Script-only — Tokscale handles data, Python formats it. Zero LLM tokens burned. |
| `--deliver` | `origin` | Sends report back to this chat (Telegram) |
| `--schedule` | `0 8 * * 1` | Weekly Monday 8AM — enough to track trends |
| Profile | **default** | Tracks all profiles' spend in one place |

**Alternative: Daily report** (if you want tighter monitoring):
```bash
hermes cron create \
  --name "Token Utilization Report" \
  --schedule "0 8 * * *" \
  --script token-util-report.sh \
  --no-agent \
  --deliver origin
```

### Step 5: Log Setup Completion

```bash
mkdir -p ~/.gbrain/integrations/token-utilization
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","event":"setup_complete","version":"1.0.0","status":"ok"}' >> ~/.gbrain/integrations/token-utilization/heartbeat.jsonl
```

## What the Report Looks Like

```
# 🤖 Token Utilization — 2026-06-22

## 📊 Monthly Summary

| Month | Input Tokens | Output Tokens | Cache Reads | Messages | Cost |
|-------|-------------|--------------|-------------|----------|------|
| 2026-05 | 432,469,185 | 12,682,659 | 1,966,328,727 | 44,362 | $93.65 |
| 2026-06 | 409,537,610 | 8,398,872 | 1,228,404,480 | 39,170 | $51.74 |
| **Total** | | | | | **$145.39** |

## 🧠 This Month — Per Model

| Client | Model | Input | Output | Cache Read | Messages | Cost |
|--------|-------|-------|--------|------------|----------|------|
| hermes | deepseek-v4-flash | 366,471,500 | 14,218,893 | 2,231,377,276 | 46,084 | $57.82 |
| hermes | deepseek/deepseek-v4-flash | 426,690,855 | 5,972,517 | 879,786,496 | 28,197 | $63.28 |

## ⚡ Today (2026-06-21)

**1,247 messages** — **$1.84**

| Model | Messages | Cost |
|-------|----------|------|
| deepseek-v4-flash | 986 | $1.21 |
| deepseek/deepseek-v4-flash | 261 | $0.63 |

## 🚨 Observations

- ⚠️ High spend on **deepseek/deepseek-v4-flash**: $63.28 this month
```

## Customization

**Tuning the script:**
- Change `--today` to `--week` for a 7-day window in the daily section
- Add `--client hermes` to filter to Hermes-only if you use other clients
- Add cost alerts by editing the observations section threshold (`e['cost'] > 20`)

## Cost

$0 — Tokscale is free. The script runs in under 5 seconds with zero API calls.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Empty report | Tokscale may not have data yet. Run `tokscale --light` to verify. |
| `TOKSCALE_ERROR` | Tokscale CLI not in PATH. Update script to use absolute path. |
| Missing profiles | Check `~/.config/tokscale` scanner config — add missing profile state.db paths. |
| Cost shows $0 for a model | Tokscale missing pricing data. Usually for very new models — check LiteLLM pricing. |
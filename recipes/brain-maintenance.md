---
name: brain-maintenance
category: ops
setup_time: 15 min
cost: $0
depends_on: [gbrain]
---

# Brain Maintenance

Health checks, orphan detection, link campaigns, compliance validation, and dream cycle scheduling for gbrain. Keeps your knowledge base clean, connected, and up-to-date.

## Architecture

```
Daily Health Check (cron 6AM)
  └── gbrain doctor → structured report

Weekly Orphan Sweep (cron Mon 7AM)
  └── gbrain orphans → link campaign

Weekly Compliance (cron Mon 8AM)
  └── gbrain compliance validate

Dream Cycle (cron every 2h)
  └── gbrain dream cycle
```

## Setup

### Step 1: Create the health check script

Write to `~/.hermes/scripts/brain-health-check.sh`:

```bash
#!/bin/bash
# Brain health check — runs gbrain doctor and reports structured results
set -euo pipefail

echo "=== Brain Health Check @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo ""

# 1. Run gbrain doctor
echo "## gbrain doctor"
gbrain doctor 2>&1 || echo "⚠️  gbrain doctor returned non-zero"

echo ""
echo "## Brain stats"
gbrain stats 2>&1 || true

echo ""
echo "## Orphan pages"
gbrain orphans 2>&1 || true
```

Make it executable:

```bash
chmod +x ~/.hermes/scripts/brain-health-check.sh
```

### Step 2: Create the link campaign script

Write to `~/.hermes/scripts/brain-link-campaign.sh`:

```bash
#!/bin/bash
# Weekly link campaign — finds orphans and suggests backlinks
set -euo pipefail

echo "=== Link Campaign @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Find orphan pages
ORPHANS=$(gbrain orphans --json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    pages = data.get('pages', [])
    for p in pages[:20]:
        print(p.get('slug', ''))
except:
    pass
" 2>/dev/null)

if [ -z "$ORPHANS" ]; then
    echo "✅ No orphan pages found."
    exit 0
fi

echo "📋 Found $(echo "$ORPHANS" | wc -l) orphan pages:"
echo "$ORPHANS" | while read -r slug; do
    echo "  - $slug"
done
```

Make it executable:

```bash
chmod +x ~/.hermes/scripts/brain-link-campaign.sh
```

### Step 3: Create compliance validation script

Write to `~/.hermes/scripts/brain-compliance-check.sh`:

```bash
#!/bin/bash
# Compliance validation — checks YAML frontmatter, required fields, naming conventions
set -euo pipefail

echo "=== Compliance Check @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Check frontmatter consistency
python3 << 'PYEOF'
import os, re, yaml
from pathlib import Path

brain_dir = Path.home() / "brain"
issues = 0
total = 0

for md_file in brain_dir.rglob("*.md"):
    total += 1
    content = md_file.read_text()
    if not content.startswith("---"):
        print(f"  ⚠️  {md_file.relative_to(brain_dir)}: Missing frontmatter")
        issues += 1
        continue
    try:
        _, fm_str, _ = content.split("---", 2)
        fm = yaml.safe_load(fm_str)
        if not fm or not isinstance(fm, dict):
            print(f"  ⚠️  {md_file.relative_to(brain_dir)}: Invalid frontmatter")
            issues += 1
        elif "type" not in fm:
            print(f"  ⚠️  {md_file.relative_to(brain_dir)}: Missing 'type' in frontmatter")
            issues += 1
    except Exception as e:
        print(f"  ⚠️  {md_file.relative_to(brain_dir)}: YAML error: {e}")
        issues += 1

print(f"  Checked {total} pages, {issues} issues found")
PYEOF
```

Make it executable:

```bash
chmod +x ~/.hermes/scripts/brain-compliance-check.sh
```

### Step 4: Create the cron jobs

```bash
# Daily health check
hermes cron create \
  --name "Brain Health Check" \
  --schedule "0 6 * * *" \
  --script brain-health-check.sh \
  --no-agent \
  --deliver local

# Weekly orphan link campaign
hermes cron create \
  --name "Brain Link Campaign" \
  --schedule "0 7 * * 1" \
  --script brain-link-campaign.sh \
  --no-agent \
  --deliver local

# Weekly compliance validation
hermes cron create \
  --name "Brain Compliance Check" \
  --schedule "0 8 * * 1" \
  --script brain-compliance-check.sh \
  --no-agent \
  --deliver local

# Dream cycle (every 2 hours)
hermes cron create \
  --name "Brain Dream Cycle" \
  --schedule "0 */2 * * *" \
  --script gbrain-dream-cycle.sh \
  --no-agent \
  --deliver local
```

## Cron Jobs

| Name | Schedule | Script | Agent | Delivery |
|------|----------|--------|-------|----------|
| Brain Health Check | `0 6 * * *` | `brain-health-check.sh` | No | `local` |
| Brain Link Campaign | `0 7 * * 1` | `brain-link-campaign.sh` | No | `local` |
| Brain Compliance Check | `0 8 * * 1` | `brain-compliance-check.sh` | No | `local` |
| Brain Dream Cycle | `0 */2 * * *` | `gbrain-dream-cycle.sh` | No | `local` |

## Config

No additional config required beyond a working gbrain installation. The scripts use `gbrain doctor`, `gbrain stats`, `gbrain orphans` — ensure these CLI commands are available.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| gbrain doctor fails | Run `gbrain doctor` manually to see the actual error. Common: Postgres not running, or brain path not configured |
| Orphan count too high | Ignore auto-generated pages with `--include-pseudo=false` |
| Compliance false positives | Adjust the frontmatter validation script to match your conventions |
| Dream cycle slow | Reduce frequency — every 4h instead of 2h |
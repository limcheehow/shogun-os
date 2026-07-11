---
name: brain-maintenance
category: ops
setup_time: 10
cost: $0
depends_on: [gbrain]
---

# Brain Health Maintenance

Automated brain health checks, orphan detection, link campaigns, and compliance validation.

## Setup

1. Ensure gbrain is installed and configured:
```bash
gbrain --version  # v0.42.x+
```

2. Create cron jobs:
```bash
# Daily health check
cronjob action=create schedule='0 9 * * *' name='brain-health-check' \
  prompt='Run gbrain doctor and report any issues. Use mcp_gbrain_run_doctor tool.' \
  deliver=local

# Daily auto-link campaign (reduce orphans)
cronjob action=create schedule='0 2 * * *' name='brain-auto-link' \
  prompt='Run brain link campaign: find orphans, create links between related pages. Use mcp_gbrain_find_orphans and mcp_gbrain_brain_link_campaign tools.' \
  deliver=local

# Daily dream cycle (consolidation + embedding)
cronjob action=create schedule='0 2 * * *' name='gbrain-dream-cycle' \
  script='gbrain-dream-cycle.sh' no_agent=true deliver=local
```

## Cron Jobs

| Job | Schedule | Type | Purpose |
|-----|----------|------|---------|
| Brain Health Check | Daily 9AM | Agent | `gbrain doctor` + issue report |
| Auto-Link Campaign | Daily 2AM | Agent | Orphan detection + link creation |
| Dream Cycle | Daily 2AM | no_agent | Consolidation + embedding refresh |

## Config

No additional config needed — uses gbrain MCP tools directly.

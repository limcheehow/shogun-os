---
name: profile-provisioning
category: ops
setup_time: 5
cost: $0
depends_on: [hermes-agent]
---

# Profile Provisioning

Create and manage Hermes Agent profiles with SOUL.md, config.yaml, and systemd services.

## Setup

1. Use the profile generator:
```bash
python3 scripts/generate-profile.py hr-manager --type hr
python3 scripts/generate-profile.py crm-manager --type crm --force
```

2. Enable the systemd service:
```bash
systemctl --user enable --now hermes-gateway@hr-manager
```

3. Verify:
```bash
systemctl --user status hermes-gateway@hr-manager
hermes --profile hr-manager gateway list
```

## What Each Profile Gets

| File | Purpose |
|------|---------|
| `SOUL.md` | Persona + boundaries + **workflow enforcement snippet** |
| `config.yaml` | Model config + MCP servers + platform connection |
| `.env` | Secrets (API keys, bot tokens) |
| `skills/` | Symlinks to shared skills + profile-specific skills |
| `cron.db` | Profile-scoped cron jobs |

## SOUL.md Workflow Enforcement

Every generated SOUL.md includes a mandatory `## Workflow Enforcement (MANDATORY)` section that enforces the 6-gate sequence (Triage → RCA → Brainstorm → Plan → TDD → E2E) for any feature/bug request.

The `company-workflow` skill is included in every profile type's skill list.

## Config

```yaml
# templates/profiles/base-config.yaml uses placeholder variables:
model:
  default: deepseek-v4-flash
  provider: custom
  base_url: ${PRIMARY_PROVIDER_BASE_URL}
  api_key: ${PRIMARY_PROVIDER_API_KEY}

fallback_providers:
  - provider: ${BACKUP_PROVIDER_NAME}
    model: ${BACKUP_PROVIDER_MODEL}
```

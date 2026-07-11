---
name: model-health-auto-fallback
category: infra
setup_time: 10
cost: $0
depends_on: []
---

# Model Health Auto-Fallback

Automatic provider health monitoring with switchover to backup on failure and recovery switching.

## Setup

1. Deploy the health check script:
```bash
cp scripts/model-health-check.sh ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/model-health-check.sh
```

2. Configure primary and backup providers in `~/.hermes/config.yaml`:
```yaml
model:
  default: your-primary-model
  provider: custom
  base_url: ${PRIMARY_PROVIDER_BASE_URL}
  api_key: ${PRIMARY_PROVIDER_API_KEY}

fallback_providers:
  - provider: ${BACKUP_PROVIDER_NAME}
    model: ${BACKUP_PROVIDER_MODEL}
```

3. Create the cron job:
```bash
cronjob action=create schedule='*/5 * * * *' name='model-health-check' \
  script='model-health-check.sh' no_agent=true deliver=local
```

## How It Works

1. Script pings the primary provider with a lightweight request (`max_tokens: 5`)
2. If primary fails and we're on primary → switch to backup, restart gateway
3. If primary recovers and we're on backup → switch back to primary, restart gateway
4. Silent (exit 0) when already on the correct provider — no notification spam

## Config

```yaml
# The script reads from config.yaml automatically.
# No additional config needed — it uses the existing model/fallback_providers fields.

# Optional: override the health check endpoint
# HEALTH_CHECK_MODEL: "tiny"  # Use a small model for the ping
```

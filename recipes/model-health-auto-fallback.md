---
name: model-health-auto-fallback
id: model-health-auto-fallback
category: ops
setup_time: 10 min
cost: $0
depends_on: []
---

# Model Health Auto-Fallback

Provider health check cron + auto-switchover. Pings the primary LLM provider, auto-switches all profiles to a backup provider on failure, and switches back when the primary recovers. Config-driven — reads provider settings from each profile's config.yaml.

## Architecture

```
cron (every 5 min)
  ↓ script=model-health-check.sh (no_agent)
model-health-check.sh
  ├── Pings PRIMARY provider endpoint
  │   ├── 200 OK → already on primary? Silent. On fallback? Switch back.
  │   └── Error → already on fallback? Silent. On primary? Switch to fallback.
  ├── Updates ALL profile config.yaml files (model, provider, base_url, api_key, api_mode)
  └── Tracks state in ~/.hermes/model_fallback_state ("primary" | "fallback")
```

## Setup

### Step 1: Create the health check script

Copy `scripts/model-health-check.sh` from this repo to `~/.hermes/scripts/`:

```bash
cp scripts/model-health-check.sh ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/model-health-check.sh
```

### Step 2: Configure provider settings

Edit the `PRIMARY_*` and `FALLBACK_*` variables at the top of `model-health-check.sh`:

```bash
# ── Primary (your daily provider) ──
PRIMARY_MODEL="your-primary-model"
PRIMARY_PROVIDER="custom"
PRIMARY_BASE_URL="https://primary-provider.example.com/v1"
PRIMARY_API_KEY="$PRIMARY_API_KEY"  # Set via .env
PRIMARY_API_KEY_VAR='${PRIMARY_API_KEY}'
PRIMARY_API_MODE="chat_completions"

# ── Fallback (backup when primary is down) ──
FALLBACK_MODEL="your-backup-model"
FALLBACK_PROVIDER="backup-provider"
FALLBACK_BASE_URL="https://backup-provider.example.com/api/v1"
FALLBACK_API_KEY_VAR='${BACKUP_API_KEY}'
FALLBACK_API_MODE="chat_completions"
```

### Step 3: Ensure API keys are in .env

The script sources `~/.hermes/.env` for API keys. Add:

```bash
export PRIMARY_API_KEY="sk-..."
export BACKUP_API_KEY="sk-..."
```

### Step 4: Create the cron job

```bash
hermes cron create \
  --name "Model Health Auto-Fallback" \
  --schedule "*/5 * * * *" \
  --script model-health-check.sh \
  --no-agent \
  --deliver local
```

### Step 5: Verify

```bash
# Run manually to test
bash ~/.hermes/scripts/model-health-check.sh

# Check state
cat ~/.hermes/model_fallback_state
# Should print "primary"

# Simulate failure (temporarily set wrong URL)
PRIMARY_BASE_URL="https://invalid.example.com" bash ~/.hermes/scripts/model-health-check.sh
# Should print "Primary API is DOWN! Switching ALL profiles to fallback..."
```

## Cron Jobs

| Name | Schedule | Script | Agent | Delivery |
|------|----------|--------|-------|----------|
| Model Health Auto-Fallback | `*/5 * * * *` | `model-health-check.sh` | No | `local` |

## Config

### model-health-check.sh configuration variables

```yaml
# The script reads these from the top of the file (edit directly):
# PRIMARY_MODEL: "your-primary-model"
# PRIMARY_PROVIDER: "custom"
# PRIMARY_BASE_URL: "https://primary-provider.example.com/v1"
# PRIMARY_API_KEY_VAR: '${PRIMARY_API_KEY}'
# PRIMARY_API_MODE: "chat_completions"
# 
# FALLBACK_MODEL: "your-backup-model"
# FALLBACK_PROVIDER: "backup-provider"
# FALLBACK_BASE_URL: "https://backup-provider.example.com/api/v1"
# FALLBACK_API_KEY_VAR: '${BACKUP_API_KEY}'
# FALLBACK_API_MODE: "chat_completions"
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Script can't find .env | Ensure `~/.hermes/.env` exists with the API key variables |
| Switching fails silently | Check `~/.hermes/model_fallback_state` — if it's missing, the script hasn't run |
| Config files corrupted | The script uses `sed -i` to replace model section lines. If the config.yaml format changes, the sed patterns may miss |
| Endpoint returns 404 | The script tries `/v1/chat/completions` and strips `/v1` if base_url already ends with it. Check your provider's actual endpoint |
| "PRIMARY_API_KEY is empty" | The variable name in the script must match the .env variable name |
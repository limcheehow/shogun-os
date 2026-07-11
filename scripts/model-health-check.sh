#!/bin/bash
# Model Health Auto-Fallback — watchdog script
# Periodically pings the primary API and auto-switches ALL profiles
# (main + each profile with its own model section) to a fallback config
# when the primary is down. Switches back when it recovers.
#
# Silent watchdog mode: produces NO output when healthy — only notifies
# on actual switch events. Pair with cron `no_agent=true` for zero-spam
# delivery: script stdout is delivered verbatim only on switch.
#
# Usage: bash ~/.hermes/scripts/model-health-check.sh
# Or via cron: script=model-health-check.sh (from ~/.hermes/scripts/)
#
# State tracked in STATE_FILE: "primary" or "fallback".
#
# CONFIG: Edit the PRIMARY / FALLBACK sections below, or better yet,
# create a config file at $HOME/.hermes/model-health-config.yaml
# and source it from there. See scripts/config.yaml.example for structure.

set -euo pipefail

# ── Load .env for API keys ──
DEFAULT_ENV="$HOME/.hermes/.env"
if [ -f "$DEFAULT_ENV" ]; then
    set -a
    source "$DEFAULT_ENV"
    set +a
fi

STATE_FILE="$HOME/.hermes/model_fallback_state"

# ═══════════════ EDIT THESE ═══════════════
# PRIMARY_API_KEY = the env var name holding the primary API key
#   The script reads this from .env via source above. Set the variable name below.
# PRIMARY_API_KEY_VAR = literal string written to config.yaml api_key field (e.g. '${ENV_VAR_NAME}')
#   Use single quotes around ${ENV_VAR} so bash doesn't expand it.
# PRIMARY_API_MODE = "anthropic_messages" (Anthropic /v1/messages) or "chat_completions" (OpenAI /v1/chat/completions)
#   anthropic_messages → /v1/messages endpoint, x-api-key header
#   chat_completions  → /v1/chat/completions endpoint, Authorization: Bearer ***

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

# ══════════════════════════════════════════

# ── Detect profiles with their own model section ──
PROFILES_WITH_MODEL=()
for p in "$HOME/.hermes/profiles/"*/config.yaml; do
    name=$(basename "$(dirname "$p")")
    if grep -q "^model:" "$p" 2>/dev/null; then
        PROFILES_WITH_MODEL+=("$name")
    fi
done

# ── Read current state ──
ON_FALLBACK=false
if [ -f "$STATE_FILE" ]; then
    STATE=$(cat "$STATE_FILE")
    if [ "$STATE" = "fallback" ]; then
        ON_FALLBACK=true
    fi
fi

# ── Health check: ping primary API ──
check_primary() {
    if [ -z "$PRIMARY_API_KEY" ]; then
        echo "  ⚠️  PRIMARY_API_KEY is empty — skipping health check"
        return 1
    fi

    local response

    if [ "$PRIMARY_API_MODE" = "anthropic_messages" ]; then
        response=$(curl -s -w "\n%{http_code}" --max-time 15 \
            "${PRIMARY_BASE_URL}/v1/messages" \
            -H "Content-Type: application/json" \
            -H "x-api-key: ${PRIMARY_API_KEY}" \
            -H "anthropic-version: 2023-06-01" \
            -d '{
                "model": "'"$PRIMARY_MODEL"'",
                "messages": [{"role": "user", "content": "Reply with just the word ok."}],
                "max_tokens": 10
            }' 2>/dev/null)
    else
        # OpenAI chat completions format
        local url="${PRIMARY_BASE_URL}/v1/chat/completions"
        if echo "$PRIMARY_BASE_URL" | grep -q "/v1$"; then
            url="${PRIMARY_BASE_URL}/chat/completions"
        fi
        response=$(curl -s -w "\n%{http_code}" --max-time 15 \
            "$url" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${PRIMARY_API_KEY}" \
            -d '{
                "model": "'"$PRIMARY_MODEL"'",
                "messages": [{"role": "user", "content": "Reply with just the word ok."}],
                "max_tokens": 10
            }' 2>/dev/null)
    fi

    local http_code
    http_code=$(echo "$response" | tail -1)
    [ "$http_code" = "200" ] && return 0 || return 1
}

# ── Update one config file's model section via sed ──
update_config() {
    local config_file="$1"
    local model="$2"
    local provider="$3"
    local base_url="$4"
    local api_key="$5"
    local api_mode="$6"
    local label="$7"

    sed -i "s|^  default:.*|  default: $model|" "$config_file"
    sed -i "s|^  provider:.*|  provider: $provider|" "$config_file"
    sed -i "s|^  base_url:.*|  base_url: $base_url|" "$config_file"
    sed -i "s|^  api_key:.*|  api_key: $api_key|" "$config_file"
    sed -i "s|^  api_mode:.*|  api_mode: $api_mode|" "$config_file"
    echo "  ✓ $label: $model ($provider) | api_mode=$api_mode"
}

# ── Switch ALL configs to primary ──
# Writes resolved env var values (actual keys) to profile configs so they
# don't depend on profile .env files which lack these variables.
# The default config keeps env-var references for security.
switch_to_primary() {
    echo "Primary API recovered. Switching ALL profiles back to primary..."
    update_config "$HOME/.hermes/config.yaml" "$PRIMARY_MODEL" "$PRIMARY_PROVIDER" "$PRIMARY_BASE_URL" "$PRIMARY_API_KEY_VAR" "$PRIMARY_API_MODE" "Main"
    for prof in "${PROFILES_WITH_MODEL[@]}"; do
        update_config "$HOME/.hermes/profiles/$prof/config.yaml" \
            "$PRIMARY_MODEL" "$PRIMARY_PROVIDER" "$PRIMARY_BASE_URL" "$PRIMARY_API_KEY" "$PRIMARY_API_MODE" "Profile: $prof"
    done
    echo "primary" > "$STATE_FILE"
    echo ""
    echo "✅ Switched ALL profiles to PRIMARY: $PRIMARY_MODEL ($PRIMARY_PROVIDER) | mode=$PRIMARY_API_MODE"
}

# ── Switch ALL configs to fallback ──
# Writes resolved env var values (actual keys) to profile configs so they
# don't depend on profile .env files which lack these variables.
switch_to_fallback() {
    echo "Primary API is DOWN! Switching ALL profiles to fallback..."
    update_config "$HOME/.hermes/config.yaml" "$FALLBACK_MODEL" "$FALLBACK_PROVIDER" "$FALLBACK_BASE_URL" "$FALLBACK_API_KEY_VAR" "$FALLBACK_API_MODE" "Main"
    for prof in "${PROFILES_WITH_MODEL[@]}"; do
        update_config "$HOME/.hermes/profiles/$prof/config.yaml" \
            "$FALLBACK_MODEL" "$FALLBACK_PROVIDER" "$FALLBACK_BASE_URL" "$BACKUP_API_KEY" "$FALLBACK_API_MODE" "Profile: $prof"
    done
    echo "fallback" > "$STATE_FILE"
    echo ""
    echo "✅ Switched ALL profiles to FALLBACK: $FALLBACK_MODEL ($FALLBACK_PROVIDER) | mode=$FALLBACK_API_MODE"
}

# ── Main — silent watchdog (only output on actual switch) ──
if [ -z "$PRIMARY_API_KEY" ]; then
    echo "❌ PRIMARY_API_KEY variable not set. Cannot check health."
    exit 1
fi

if check_primary; then
    if [ "$ON_FALLBACK" = true ]; then
        switch_to_primary
    fi
else
    if [ "$ON_FALLBACK" = true ]; then
        :
    else
        switch_to_fallback
    fi
fi
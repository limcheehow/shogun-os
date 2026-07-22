#!/usr/bin/env bash
# Wrapper for support-email-poller.py — reads env vars from profile .env
set -euo pipefail

PROFILE="${HERMES_PROFILE:-project-manager}"
ENV_FILE="$HOME/.hermes/profiles/$PROFILE/.env"

if [ -f "$ENV_FILE" ]; then
    # Only export the vars we need (avoid leaking other secrets)
    export SLACK_BOT_TOKEN="$(grep '^SLACK_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)"
    export SUPPORT_SLACK_CHANNEL="${SUPPORT_SLACK_CHANNEL:-}"
    export GMAIL_USER="${GMAIL_USER:-}"
    export SERVICE_ACCOUNT_FILE="${SERVICE_ACCOUNT_FILE:-$HOME/.hermes/service-account-key.json}"
fi

exec python3 "$(dirname "$0")/support-email-poller.py" "$@"
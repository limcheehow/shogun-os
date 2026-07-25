---
name: jibble
category: connector
setup_time: 10
cost: $0
depends_on: []
---

# Jibble — Time Tracking Provider Setup

> **Cloud-based time tracking with GPS, geofencing, and selfie verification.** 
> Implements the [CONTRACT.md](../CONTRACT.md) standard tools.

## Setup

### 1. Get API Credentials

1. Log in to your Jibble dashboard
2. Go to **Integrations → API Keys**
3. Generate an API key
4. (Optional) Note your base URL if different from default

### 2. Configure the MCP Server

```yaml
mcp_servers:
  time-tracking:
    command: python3
    args: [~/.hermes/scripts/tt-bridge-jibble.py]
    env:
      TT_API_KEY: "${TT_API_KEY}"
      TT_BASE_URL: "https://api.jibble.io/v1"
```

### 3. Set the API Key

```bash
echo 'TT_API_KEY="your-jibble-api-key"' >> ~/.hermes/profiles/hr-manager/.env
```

### 4. Verify

```bash
echo '{"id":1,"method":"tools/call","params":{"name":"tt_current_status","arguments":{}}}' \
  | python3 ~/.hermes/scripts/tt-bridge-jibble.py
# Expected: JSON with active members list
```

## Notes

- Jibble uses `X-Api-Key` header auth
- GPS data comes from the mobile app clock-in
- Geofencing is configured in Jibble admin, not in the bridge
- The bridge implements all 5 P0 tools from the contract
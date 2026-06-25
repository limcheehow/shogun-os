# Kami — Time Tracking Provider Setup

> **Malaysian GPS time tracking app.** Local support, geofencing, selfie clock-in.
> Implements the [CONTRACT.md](CONTRACT.md) standard tools via a custom bridge.

## Setup

### 1. Get API Credentials

1. Log in to your Kami admin dashboard
2. Go to **Settings → Integrations → API**
3. Generate an API key
4. Note your organization ID (shown in URL or Settings)

### 2. Write the Bridge

Create `~/.hermes/scripts/tt-bridge-kami.py` following the bridge pattern from [bridges/tt-bridge-jibble.py](bridges/tt-bridge-jibble.py), mapping:

| Standard Tool | Kami API Endpoint |
|--------------|-------------------|
| `tt_current_status` | `GET /api/v1/attendance/active` |
| `tt_get_entries` | `GET /api/v1/attendance?start=X&end=Y` |
| `tt_get_members` | `GET /api/v1/employees` |
| `tt_get_projects` | `GET /api/v1/projects` |
| `tt_create_project` | `POST /api/v1/projects` |

> **Tip:** Kami's API uses `X-API-Key` header auth (not Bearer). Base URL varies by org plan.

### 3. Configure the MCP Server

```yaml
mcp_servers:
  time-tracking:
    command: python3
    args: [~/.hermes/scripts/tt-bridge-kami.py]
    env:
      TT_API_KEY: "${TT_API_KEY}"
      TT_BASE_URL: "https://your-org.kami.workers.dev/api/v1"
```

### 4. Set the API Key

```bash
echo 'TT_API_KEY="kami_sk_..."' >> ~/.hermes/profiles/hr-manager/.env
```

### 5. Verify

```bash
echo '{"id":1,"method":"tools/call","params":{"name":"tt_current_status","arguments":{}}}' \
  | python3 ~/.hermes/scripts/tt-bridge-kami.py
# Expected: JSON with active members list
```

## Notes

- Kami GPS data comes from the mobile app clock-in
- Geofencing is configured in Kami admin, not in the bridge
- Selfie verification happens at clock-in time in the mobile app
- The bridge only surfaces data the API exposes — GPS lat/lng may require enterprise plan
---
name: xero
category: connector
setup_time: 20
cost: $0
depends_on: []
---

# Xero — Accounting Provider Setup

> **Global cloud accounting platform.** Strong in Australia, New Zealand, UK, and Southeast Asia.
> Implements the [CONTRACT.md](CONTRACT.md) standard tools via the unified bridge.

## Setup

### 1. Create a Xero App

1. Go to [developer.xero.com/app/manage](https://developer.xero.com/app/manage)
2. Create a new app
3. Enable scopes: `openid`, `profile`, `email`, `accounting.transactions`, `accounting.settings`, `accounting.reports.read`, `accounting.contacts`, `offline_access`
4. Note your **Client ID** and **Client Secret**
5. Set the redirect URI to your OAuth callback

### 2. Get OAuth Tokens

1. Authorize URL: `https://login.xero.com/identity/connect/authorize?client_id=YOUR_CLIENT_ID&response_type=code&scope=openid+profile+email+accounting.transactions+accounting.settings+accounting.reports.read+accounting.contacts+offline_access&redirect_uri=YOUR_REDIRECT_URI`
2. Exchange the authorization code for access + refresh tokens
3. Note your **Tenant ID** (organisation ID) — found in Xero settings or via the `GET /connections` API

### 3. Configure the MCP Server

```yaml
mcp_servers:
  accounting:
    command: python3
    args: [~/.hermes/scripts/acct-bridge.py]
    env:
      ACCT_PROVIDER: "xero"
      ACCT_API_KEY: "${ACCT_API_KEY}"
      ACCT_CLIENT_ID: "${ACCT_CLIENT_ID}"
      ACCT_CLIENT_SECRET: "${ACCT_CLIENT_SECRET}"
      ACCT_REFRESH_TOKEN: "${ACCT_REFRESH_TOKEN}"
      ACCT_TENANT_ID: "${ACCT_TENANT_ID}"
```

### 4. Set Environment Variables

```bash
# In the profile's .env (e.g., ~/.hermes/profiles/finance-manager/.env)
ACCT_PROVIDER=xero
ACCT_API_KEY=initial-access-token
ACCT_CLIENT_ID=your-xero-client-id
ACCT_CLIENT_SECRET=your-xero-client-secret
ACCT_REFRESH_TOKEN=your-xero-refresh-token
ACCT_TENANT_ID=your-xero-tenant-id
```

### 5. Verify

```bash
echo '{"id":1,"method":"tools/call","params":{"name":"acct_list_contacts","arguments":{"limit":5}}}' \
  | python3 ~/.hermes/scripts/acct-bridge.py
# Expected: JSON with contacts list
```

## Notes

- Xero uses OAuth2 — tokens are cached at `~/.hermes/mcp-tokens/accounting-xero.json`
- The bridge auto-refreshes tokens using the `oauth-helper.py` module
- Both invoices and bills use the same `/Invoices` endpoint, differentiated by `Type`:
  - `ACCREC` = Accounts Receivable (sales invoices)
  - `ACCPAY` = Accounts Payable (purchase bills)
- Xero uses UUIDs for IDs, not integers
- The `Xero-tenant-id` header is required for all API calls
- Xero's reports API returns structured data that may need parsing — the bridge returns the raw report structure
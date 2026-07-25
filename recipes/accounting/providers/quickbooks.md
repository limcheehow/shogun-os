---
name: quickbooks
category: connector
setup_time: 20
cost: $0
depends_on: []
---

# QuickBooks Online — Accounting Provider Setup

> **Global cloud accounting platform by Intuit.** Suitable for businesses of all sizes.
> Implements the [CONTRACT.md](CONTRACT.md) standard tools via the unified bridge.

## Setup

### 1. Create a QuickBooks Online App

1. Go to [developer.intuit.com/appbuilder](https://developer.intuit.com/appbuilder)
2. Create a new app (or use existing)
3. Enable **Accounting API** scope
4. Note your **Client ID** and **Client Secret**
5. Set the OAuth redirect URI to `https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl`
6. Note your **Company ID** (Realm ID) — found in the URL when logged into QBO

### 2. Get OAuth Tokens

Use the OAuth 2.0 Playground or your own flow:

1. Authorize URL: `https://appcenter.intuit.com/connect/oauth2?client_id=YOUR_CLIENT_ID&response_type=code&scope=com.intuit.quickbooks.accounting&redirect_uri=YOUR_REDIRECT_URI`
2. Exchange the authorization code for access + refresh tokens
3. The access token expires in 1 hour; the bridge auto-refreshes using `oauth-helper.py`

### 3. Configure the MCP Server

```yaml
mcp_servers:
  accounting:
    command: python3
    args: [~/.hermes/scripts/acct-bridge.py]
    env:
      ACCT_PROVIDER: "quickbooks"
      ACCT_API_KEY: "${ACCT_API_KEY}"
      ACCT_CLIENT_ID: "${ACCT_CLIENT_ID}"
      ACCT_CLIENT_SECRET: "${ACCT_CLIENT_SECRET}"
      ACCT_REFRESH_TOKEN: "${ACCT_REFRESH_TOKEN}"
      ACCT_COMPANY_ID: "${ACCT_COMPANY_ID}"
```

### 4. Set Environment Variables

```bash
# In the profile's .env (e.g., ~/.hermes/profiles/finance-manager/.env)
ACCT_PROVIDER=quickbooks
ACCT_API_KEY=initial-access-token
ACCT_CLIENT_ID=your-qb-client-id
ACCT_CLIENT_SECRET=your-qb-client-secret
ACCT_REFRESH_TOKEN=your-qb-refresh-token
ACCT_COMPANY_ID=your-company-realm-id
```

### 5. Verify

```bash
echo '{"id":1,"method":"tools/call","params":{"name":"acct_list_contacts","arguments":{"limit":5,"type":"customer"}}}' \
  | python3 ~/.hermes/scripts/acct-bridge.py
# Expected: JSON with customer list
```

## Notes

- QBO uses OAuth2 — tokens are cached at `~/.hermes/mcp-tokens/accounting-quickbooks.json`
- The bridge auto-refreshes tokens using the `oauth-helper.py` module
- QBO uses a query language instead of REST endpoints for listing
- For sandbox testing, set `ACCT_SANDBOX=true` in the profile's `.env`
- QBO items are called "Products" in the contract — mapped from `Item` entity
- Voiding is done via a dedicated void endpoint, not PATCH
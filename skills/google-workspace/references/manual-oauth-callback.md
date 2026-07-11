# Manual OAuth Callback Flow (Fallback)

When `setup.py` fails, hangs, or the port-1 redirect doesn't work (common on
WSL where the user's browser is on Windows but the server is in WSL), use
this manual fallback approach.

## Why This Works

The Desktop App OAuth client's redirect URI is `http://localhost`. Google
accepts `http://localhost:<PORT>` for any port — not just port 80. By
starting a real HTTP server on an available port (e.g., 18081) and setting
`redirect_uri=http://localhost:18081`, the browser redirects directly to your
server after authorization. The user sees "Authorized" and can close the tab.

**WSL note**: Windows Chrome can reach WSL servers via `localhost:<PORT>`
— no IP address gymnastics needed.

## When to Use

- `setup.py` times out, hangs, or produces errors
- `webbrowser` module can't open a browser (headless server)
- Browser shows "Connection refused" after the port-1 redirect
- You want the user to see a clean "Authorized" page instead of a broken tab

## Implementation

### 1. Write the OAuth callback server

Create a self-contained Python script. Key points:

- **Port**: Pick a high port not commonly used (18081, 18082, etc.)
- **Bind to `0.0.0.0`** so it accepts connections from outside WSL
- **Use `threading.Thread`** to shut down the server when the code arrives
- **Output the URL** clearly so you can send it to the user
- **Run with `PYTHONUNBUFFERED=1`** so output isn't buffered in background mode

### 2. Scope selection

Include only the scopes the user needs. Common combinations:

```
# All (Gmail + Drive + Docs + Calendar + Sheets + Contacts)
"https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/contacts.readonly https://www.googleapis.com/auth/spreadsheets"

# Email only
"https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.modify"

# Docs + Drive (for reading Google Docs)
"https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/drive.readonly"
```

### 3. Token exchange

After capturing the auth code, POST to `https://oauth2.googleapis.com/token`:

```
code=<auth_code>
client_id=<client_id>
client_secret=<client_secret>
redirect_uri=http://localhost:<PORT>
grant_type=authorization_code
```

### 4. Token file format

The token must be saved in google-auth library format at
`~/.hermes/google_token.json`:

```json
{
  "token": "ya29...",
  "refresh_token": "1//0g...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "663496548802-xxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-...",
  "scopes": ["https://www.googleapis.com/auth/gmail.readonly", "..."],
  "expiry": null
}
```

The `expiry` field can be `null` — the google-auth library sets it on first use.

## Pitfalls

- **No refresh_token returned**: The user has already authorized this client
  before. Go to https://myaccount.google.com/permissions, revoke access for
  this app, then re-authorize. The `prompt=consent` param in the URL also
  helps force a fresh refresh token.
- **Port in use**: The server fails to bind. Try a different port like 18082.
- **redirect_uri mismatch**: Google redirects to `http://localhost` (port 80)
  instead of your port. The auth URL must explicitly include the port:
  `redirect_uri=http://localhost:18081` — not just `http://localhost`.
- **Client is in "Testing" state**: The user gets `Error 403: access_denied`.
  They need to go to https://console.cloud.google.com/auth/audience and add
  their Google account as a test user.
- **Browser can't reach WSL server**: Run `curl -s -o /dev/null -w "%{http_code}" http://localhost:<PORT>/`
  from a WSL terminal to verify the server is running. If curl gets a response
  but Chrome doesn't, the port may be blocked by Windows Firewall.
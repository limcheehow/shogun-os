# Web Application OAuth Client for Dashboards

When you need Google OAuth for a **web dashboard** (not CLI/Desktop), you need a **Web Application** type OAuth client — not the Desktop app type used for CLI tools.

## Key Differences

| Feature | Desktop App | Web Application |
|---|---|---|
| Redirect URIs | `http://localhost` only | Custom domains |
| JavaScript Origins | Not applicable | Required for browser flows |
| PKCE / Client Secret | PKCE flow | Client secret stored server-side |
| Use case | CLI tools, local scripts | Web apps, dashboards, auth portals |

## Google OAuth IP Address Restriction ⚠️

**Google blocks raw IP addresses** in Authorized Redirect URIs and JavaScript Origins — with one exception: `localhost`.

You CANNOT use:
```
http://52.187.147.28                        ← blocked
http://52.187.147.28/oauth2callback          ← blocked
```

You CAN use:
```
http://localhost                              ← allowed (dev)
http://localhost/oauth2callback               ← allowed (dev)
https://product.your-domain.com                  ← allowed (production)
https://product.your-domain.com/oauth2callback   ← allowed (production)
```

If the server has only a static IP and no domain, the options are:
1. Add a DNS record (A record) pointing a subdomain to the IP, then use the domain
2. Use a reverse proxy / Cloudflare tunnel that provides a domain
3. Stick with localhost-only for development and deploy with a domain

## NextAuth / Auth.js Behind a Proxy Chain

When Google sign-in runs through NextAuth (v5) behind a multi-layer proxy
(Cloudflare → Windows 443 → WSL inner port → Next.js dev/prod server), you
may hit `MissingCSRF: CSRF token was missing during an action signin`.

**Root cause**: NextAuth's CSRF token is set as a cookie on the login page.
If the proxy chain doesn't faithfully forward `Set-Cookie` headers back
through every hop, the token is lost before the callback.

**Fixes (in order of preference)**:

1. **Fix proxy header forwarding** — Ensure each proxy hop forwards
   `x-forwarded-proto: https` and `x-forwarded-host` correctly. In a
   pipe-based or Node.js proxy, check that `Set-Cookie` from the upstream
   (Next.js on :3000) reaches the browser (Windows Chrome on :443) through
   all intermediate hops.

2. **Use `trustHosted` and `cookies` config** in NextAuth:
   ```ts
   // auth.ts
   export const { handlers, auth, signIn, signOut } = NextAuth({
     trustHost: true,
     // ... rest of config
   })
   ```

3. **Bypass with redirect form action** — Instead of NextAuth's Server Action
   sign-in, use a direct form action:
   ```html
   <form action="/api/auth/signin/google">
     <button type="submit">Sign in with Google</button>
   </form>
   ```
   This bypasses the CSRF check path entirely.

4. **`skipCSRFCheck: true`** — Last resort. Only use for debugging or
   single-user dev setups. Not for production.

## Creating a Web Application OAuth Client

1. Go to https://console.cloud.google.com/apis/credentials
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Web application**
4. Fill in:

   | Field | Example |
   |---|---|
   | Name | "Dashboard Auth" |
   | Authorized JavaScript Origins | `https://product.your-domain.com`, `http://localhost` |
   | Authorized Redirect URIs | `https://product.your-domain.com/oauth2callback`, `http://localhost/oauth2callback` |

5. Click Create
6. Copy the **Client ID** and **Client Secret** — shown once

## Client Secret JSON Format

A Web Application client secret looks like:

```json
{
  "web": {
    "client_id": "663496548802-xxxx.apps.googleusercontent.com",
    "project_id": "my-project",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "GOCSPX-...",
    "redirect_uris": [
      "http://localhost/oauth2callback",
      "https://product.your-domain.com/oauth2callback"
    ],
    "javascript_origins": [
      "http://localhost",
      "https://product.your-domain.com"
    ]
  }
}
```

Note the top-level key is `"web"` — for Desktop apps it's `"installed"`.

## Switching from Desktop to Web Client

If you already have a Desktop-app OAuth client with working tokens, you can:

1. **Create a new Web Application client** (recommended) — keeps existing CLI auth working while adding dashboard auth
2. **Change the existing client type** — in GCP Console → edit the OAuth client → change Application Type to "Web application" and add the origins/URIs. Existing refresh tokens continue to work.

The **refresh tokens and access tokens live in `~/.hermes/google_token.json`** and are tied to the client ID, not the client type. Changing the type (option 2) preserves existing tokens.
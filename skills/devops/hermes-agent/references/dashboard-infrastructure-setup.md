# Dashboard Infrastructure Setup

Hermes dashboard is hosted at `product.example.com`, pointing to server `52.187.147.28`.

## Google OAuth Web Application Client

The old OAuth client was an **Installed App** type — only allowed `http://localhost` as redirect URI. It was replaced with a proper **Web Application** client for dashboard support.

| Setting | Value |
|---------|-------|
| Project | `hermes-agent-gozen` |
| Client ID | `663496548802-mocam26s9uvcqk3k1r9t43otp89p4bdu.apps.googleusercontent.com` |
| Client Secret | `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` |
| Redirect URIs | `http://localhost/oauth2callback`, `https://product.example.com/oauth2callback` |
| JS Origins | `http://localhost`, `https://product.example.com` |

**CRITICAL: Google blocks IP addresses in OAuth URIs.** You cannot use `http://52.187.147.28` or any raw IP (except `localhost`) as a redirect URI or JavaScript origin. You must use a proper domain name. This is a hard Google OAuth restriction, not a configuration error.

Saved at `~/.hermes/google_client_secret.json`.

## Cloudflare DNS

- **Domain**: example.com
- **Zone ID**: `b981f1c8f5fcd022c043a04a6ae434da`
- **Nameservers**: `dee.ns.cloudflare.com`, `leland.ns.cloudflare.com`
- **API Token**: `cfat_IkzFYVtOwHWnUIxCSJtcpFF8zz7XyOtnPvVuW93h0ff103e8` (user token in `~/.hermes/.env`)
- **Account ID**: `562ae3b0db6eecf7976a523cddca4cfc`

### Creating a DNS A Record

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/<ZONE_ID>/dns_records" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"type": "A", "name": "product", "content": "52.187.147.28", "ttl": 120, "proxied": true}'
```

#### Token Permission Gotchas

An API token can **verify itself** (`/tokens/verify` returns active) but still be **unauthorized for specific resources**. The `/zones` endpoint returns empty results or 401 if:

- The token is scoped to a different zone than the one you're querying
- The token lacks `Zone:Read` permission (needed for zone listing)
- The token has DNS edit on a zone but not zone read (you get auth error when trying to create records on that zone)

**Fix**: Use the **Edit zone DNS** template in Cloudflare Dashboard → My Profile → API Tokens. Make sure the specific zone (`example.com`) is selected. You can often find the Zone ID directly from the Cloudflare dashboard sidebar instead of trying to list zones.

### API Token Types

Cloudflare has two token formats with different capabilities:

| Type | Prefix | Can Verify | Can List Zones | Notes |
|------|--------|------------|----------------|-------|
| **Account Token** | `cfat_` | ✅ | ❌ | Created via Account API Tokens. Good for account-level operations but can't list zones even with Zone:Read. |
| **Personal Token** | `cfut_` | ✅ | ✅ | Created via My Profile → API Tokens. Full zone visibility, recommended for DNS management. |

**Lesson**: If you get "Authentication error" when creating DNS records even after the token verifies successfully, you may be using an Account token. Switch to a Personal token created with "Edit zone DNS" template scoped to the specific zone.

## WSL Networking & Port Forwarding

The Hermes server runs as WSL inside an Azure VM. Networking follows this topology:

```
Internet → Cloudflare → Azure VM (52.187.147.28) → Windows → WSL (10.0.2.4)
```

Port forwarding from the Azure VM's public IP to WSL services requires **Windows portproxy** (runs on the Windows host).

### Adding a Port Forwarding Rule

```cmd
# Run as Administrator from cmd.exe or via a .bat file
netsh interface portproxy add v4tov4 listenport=443 listenaddress=0.0.0.0 connectport=8443 connectaddress=10.0.2.4
```

This forwards: `VM:443 → WSL (10.0.2.4):8443`

### Removing a Port Forwarding Rule

```cmd
netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0
```

### Viewing All Port Proxy Rules

```cmd
netsh interface portproxy show all
```

### Opening Windows Firewall for Inbound Ports

Portproxy rules still need Windows Firewall to allow the inbound connection:

```cmd
netsh advfirewall firewall add rule name="My Service Name" dir=in action=allow protocol=TCP localport=443
```

### Common Portproxy Pitfalls

- **Requires Administrator**: `netsh interface portproxy` operations need UAC elevation. From WSL, write a `.bat` script to the Windows Desktop and tell the user to right-click → Run as Administrator.
- **No feedback on existing rules**: Adding a duplicate rule for the same `listenport:listenaddress` combo silently overwrites the old one. Deleting a non-existent rule errors out — check `show all` first.
- **Binds to Windows host**: The `listenaddress=0.0.0.0` binds to all interfaces on the Windows host, including the Azure VM's public-facing NIC. This is what makes traffic from the internet reach WSL.
- **WSL 1 vs WSL 2**: WSL 1 uses NAT mode (IP `10.0.2.x`). WSL 2 uses a virtual switch (IP `172.x.x.x`). Portproxy works with both but the connectaddress changes.
- **Ports under 1024 need elevation on the WSL side too**: If your service inside WSL needs to bind to port 80/443, either run it as root, use a port over 1024 and portproxy down to it, or use `setcap` on the binary.

### Three Layers of Network Blocking (Cloudflare 522 Diagnosis)

When debugging **Cloudflare 522 — Connection timed out** on an Azure VM:

1. **Azure NSG** — Network Security Group on the VM's NIC/subnet. This is the outermost gate and the most commonly forgotten. Check: Azure Portal → VM → Networking → Inbound port rules. Add port 443 if missing.
2. **Windows Firewall** — `netsh advfirewall firewall add rule name="..." dir=in action=allow protocol=TCP localport=443`
3. **Portproxy itself** — Verify the rule exists: `netsh interface portproxy show all`

**Diagnosis order**: 
- `localhost:PORT` works from Windows, Cloudflare doesn't → Layer 1 (Azure NSG) or Layer 2 (Windows Firewall)
- `localhost:PORT` doesn't work → Layer 3 (portproxy broken/missing) or WSL service isn't running

## SSL Termination for Cloudflare Full/Full (Strict) Mode

When Cloudflare SSL/TLS is set to **Full** or **Full (Strict)**, Cloudflare connects to the origin on port 443 (HTTPS), not port 80. If your app serves plain HTTP, you need an SSL-terminating reverse proxy on the origin.

**Do NOT change the Cloudflare SSL mode to Flexible globally** — it affects all sites on the same zone. Instead, add an SSL proxy on the origin.

### Node.js HTTPS Reverse Proxy

This approach needs no sudo and runs as the user. It generates a self-signed cert and proxies HTTPS to the HTTP backend:

```javascript
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const TARGET_HOST = '10.0.2.4';
const TARGET_PORT = 3000;
const PROXY_PORT = 8443;

const certDir = path.join(process.env.HOME, '.hermes', 'ssl');
if (!fs.existsSync(certDir)) fs.mkdirSync(certDir, { recursive: true });

const keyPath = path.join(certDir, 'server.key');
const certPath = path.join(certDir, 'server.crt');

if (!fs.existsSync(keyPath) || !fs.existsSync(certPath)) {
  const { execSync } = require('child_process');
  execSync(
    `openssl req -x509 -nodes -days 3650 -newkey rsa:2048 ` +
    `-keyout ${keyPath} -out ${certPath} ` +
    `-subj "/C=MY/ST=KL/L=KL/O=Company/CN=product.example.com" ` +
    `-addext "subjectAltName=DNS:product.example.com,DNS:localhost,IP:52.187.147.28"`
  );
}

const server = https.createServer(
  { key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) },
  (req, res) => {
    const proxyReq = http.request(
      { host: TARGET_HOST, port: TARGET_PORT, path: req.url, method: req.method,
        headers: { ...req.headers } },
      (proxyRes) => { res.writeHead(proxyRes.statusCode, proxyRes.headers); proxyRes.pipe(res); }
    );
    proxyReq.on('error', () => { res.writeHead(502); res.end('Bad Gateway'); });
    req.pipe(proxyReq);
  }
);
server.listen(PROXY_PORT, '0.0.0.0', () => {
  console.log(`HTTPS proxy on :${PROXY_PORT} → ${TARGET_HOST}:${TARGET_PORT}`);
});
```

Run it:
```bash
node ssl-proxy.js
# Or in background (survives chat sessions):
tmux new-session -d -s dashboard-proxy 'node ssl-proxy.js'
```

### Cert Generation (manual alternative)

```bash
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout ~/.hermes/ssl/server.key \
  -out ~/.hermes/ssl/server.crt \
  -subj "/C=MY/ST=KL/L=KL/O=Company/CN=product.example.com" \
  -addext "subjectAltName=DNS:product.example.com,DNS:localhost,IP:52.187.147.28"
```

### Architecture Diagram

```
User ──HTTPS──→ Cloudflare ──HTTPS──→ Azure VM:443 ──portproxy──→ WSL:8443 ──Node.js HTTPS proxy──→ Next.js:3000 (HTTP)
                  ↑                               ↑                     ↑
              Full SSL                        netsh.exe               self-signed cert
```

## Next.js Route Group Pitfall

**Problem**: The dashboard showed the default "Create Next App" starter page instead of the actual dashboard content.

**Root Cause**: Two files served the same route `/`:
- `src/app/page.tsx` — the default Create Next App template (65 lines)
- `src/app/(dashboard)/page.tsx` — the actual dashboard with Supabase data (227 lines)

Next.js will use `app/page.tsx` over `app/(dashboard)/page.tsx` when both exist. The `(dashboard)` route group is silently shadowed.

**Fix**: Delete `src/app/page.tsx` (the default starter) — the route group's page at `(dashboard)/page.tsx` will then serve as the home page at `/`. Rebuild and restart the server.

**Verification after fix**: The build output should show `/` as `ƒ /` (dynamic, server-rendered) instead of `○ /` (static, prerendered).

## NextAuth Behind Reverse Proxy (Cloudflare + HTTPS Proxy)

When running Next.js with `next-auth` behind a reverse proxy that terminates SSL:

### Configuration Error (AUTH_TRUST_HOST)

**Symptom**: Google Sign-In redirects back to the app, then hits `/api/auth/error?error=Configuration`

**Fix**: Add to `.env.local`:
```
AUTH_TRUST_HOST=true
```

Without this, NextAuth v5 rejects the forwarded host header from the reverse proxy/Cloudflare and throws a Configuration error.

**Also verify**: `AUTH_SECRET` is set (a random string, not empty), and `AUTH_URL` matches the public URL exactly including protocol:
```
AUTH_URL=https://product.example.com
```

### Supabase Adapter: Missing Auth Tables (AdapterError)

**Symptom**: After the Configuration fix, Google Sign-In proceeds but fails with a server-side `AdapterError`. Logs show `[auth][error] AdapterError`.

**Root cause**: The `@auth/supabase-adapter` needs four tables (`users`, `accounts`, `sessions`, `verification_tokens`) in the Supabase database. These are NOT created automatically — you must run a migration.

**Fix**: Run this SQL in Supabase Dashboard → SQL Editor:

```sql
create table if not exists users (
  id uuid not null default gen_random_uuid() primary key,
  name text,
  email text not null unique,
  email_verified timestamptz,
  image text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists accounts (
  id uuid not null default gen_random_uuid() primary key,
  user_id uuid not null references users(id) on delete cascade,
  type text not null,
  provider text not null,
  provider_account_id text not null,
  refresh_token text,
  access_token text,
  expires_at bigint,
  token_type text,
  scope text,
  id_token text,
  session_state text,
  created_at timestamptz default now(),
  unique(provider, provider_account_id)
);

create table if not exists sessions (
  id uuid not null default gen_random_uuid() primary key,
  user_id uuid not null references users(id) on delete cascade,
  expires timestamptz not null,
  session_token text not null unique
);

create table if not exists verification_tokens (
  identifier text not null,
  token text not null unique,
  expires timestamptz not null,
  created_at timestamptz default now(),
  unique(identifier, token)
);
```

**Pitfall**: The service role key from `.env` works for runtime queries but CANNOT create tables — the Supabase REST API (PostgREST) does not support DDL statements. You must use the Dashboard SQL Editor, `psql`, or the Supabase CLI to create table structures.

**Google blocks IP addresses (except `localhost`) in OAuth redirect URIs and JavaScript origins.** You CANNOT use:
- `http://52.187.147.28/oauth2callback`
- `http://192.168.x.x/oauth2callback`

You MUST use a proper domain name like `https://product.example.com/oauth2callback`. This is a hard Google OAuth restriction, not a configuration error.

## Next.js Build Cache Mismatch (CSS/JS 500 Errors)

**Symptom**: Pages load with HTTP 200 but all static assets (CSS, JS chunks) return HTTP 500 `Internal Server Error`. The HTML references filenames like `0g2j96z3nfpg7.css` but the actual file on disk is `0xvslpkcu-g_i.css`.

**Root cause**: The process tree was killed (e.g., `pkill -f next-server`) but restarted from an old build. The `.next` directory contains stale filenames from a previous build, while the running server serves HTML from an even older compilation that references different chunk hashes. The hashed filenames don't match.

**Fix**: Always rebuild before restarting after any code change:
```bash
cd ~/projects/tapway-product-dashboard
npx next build    # regenerates .next/ with matching hashes
npx next start -p 3000
```

**Verification**: After rebuild, the CSS filename in the HTML should match what's on disk:
```bash
curl -s http://127.0.0.1:3000/login | grep -oP '/_next/static/chunks/[^"]+\.css' | head -1
ls .next/static/chunks/*.css   # filenames should match
```

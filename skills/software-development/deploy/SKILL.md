---
name: deploy
description: Generate deployment checklist and execute deployments for  projects. Triggers include "deploy", "ship", "push to production", "release to staging".
category: software-development
---

# Deploy — Deployment Pipeline

**Route to:** coding-agent profile

## Purpose

Generate a deployment checklist and execute safe deployments following  conventions.

## Protocol

### 1. Pre-Deployment Checklist

Before any deployment:

```bash
# Verify all tests pass
make test-all 2>&1

# Verify lint is clean
make lint 2>&1

# Check git status — must be clean
git status --short

# Confirm on correct branch (develop for staging, main for prod)
git branch --show-current
```

### 2. Deployment Types

| Target | Branch | Command | What happens |
|--------|--------|---------|--------------|
| Staging | develop | Push to develop | Auto-deploy via CI |
| Production | main | Merge develop → main | Auto-deploy via CI |
| Manual | any | `make deploy` | Custom deploy script |

### 3. For the product dashboard

```bash
cd ~/projects/-product-dashboard
npm run build
```

#### Restarting the server (ad-hoc or after build)

Use `npx next start -p 3000` via `terminal(background=true)`. The server process may die silently — always verify:

```bash
# 1. Check if port 3000 is actually listening
ss -tlnp | grep 3000

# 2. If port is claimed by a zombie process (server "exited" but port still in use):
ss -tlnp | grep 3000 | awk '{print $7}'  # get pid
kill -9 <pid>
sleep 1  # give kernel time to release
```

**Pitfall:** `lsof -i :3000` can return empty even when `ss -tlnp` shows a listening process on WSL. Always use `ss -tlnp` for port checks. A background process reporting "exited" or "status: exited" does NOT mean the port was released — the node `next-server` child process can outlive the shell that spawned it.

```bash
# 3. Start fresh
cd ~/projects/-product-dashboard && npx next start -p 3000
```

### 4. Verification (post-deploy / post-restart)

Check all layers — API, Supabase, and auth — not just the homepage:

```bash
# Port listening?
ss -tlnp | grep 3000

# API endpoints (data layer)
curl -s --max-time 5 http://localhost:3000/api/tasks?limit=1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} tasks')"
curl -s --max-time 5 http://localhost:3000/api/epics?limit=3 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} epics')"

# Supabase connectivity (count endpoint)
curl -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 5 http://localhost:3000/api/tasks

# Auth middleware — homepage should 307 redirect unauthenticated users to /login
curl -s -o /dev/null -w "Status: %{http_code} → %{redirect_url}\n" --max-time 5 http://localhost:3000/

# Login page should 200
curl -s -o /dev/null -w "Status: %{http_code}\n" --max-time 5 http://localhost:3000/login

# If login is slow or times out on first hit, it's likely an auth provider cold-start
# — wait 3-5s and retry before diagnosing further

# Check server logs
tail -20 ~/projects/-product-dashboard/server.log | grep -i "ready\\|error"
```

**Pitfall: `__next_error__` in rendered output vs. 307 redirect.** If you curl the homepage and see `__next_error__` in the HTML, first check the HTTP status code:
- **200 with `__next_error__`** → a React error boundary was hit during SSR. Investigate the page component (often an unhandled Supabase query, missing env var, or auth provider crash).
- **307 redirect** → the auth middleware is working correctly (NextAuth v5 pattern). The `__next_error__` was a transient artifact from a port-conflict restart; a clean restart resolves it.

### 5. Rollback

If deployment fails:
```bash
git revert HEAD
git push
```

## Guardrails

- Never deploy directly to main — merge from develop
- Set `ALLOW_PROD=1` for production operations
- Run the full test suite before every deploy
- Check server.log after restart
- Smoke test the deployed site — verify API + Supabase + auth, not just homepage HTTP
- Kill zombie `next-server` processes with `kill -9` found via `ss -tlnp`, not `lsof` or `pkill -f`
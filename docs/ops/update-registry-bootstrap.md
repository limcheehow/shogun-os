# Update registry on Azure WSL (bootstrap tickets)

> For Hermes on the Azure Windows + WSL host that already runs `shogun-registry`.

```text
Pull latest shogun-os main and rebuild the registry container so public
install bootstrap is live.

Steps:
1. cd ~/shogun-os || cd $HOME/shogun-os
2. git fetch origin && git checkout main && git pull --ff-only origin main
3. cd shogun-web/registry
4. Ensure .env contains (add if missing):
     ENABLE_PUBLIC_BOOTSTRAP=true
     BOOTSTRAP_TICKET_TTL_SECONDS=3600
     BOOTSTRAP_RATE_LIMIT_PER_IP=10
   Do NOT remove CLOUDFLARE_* or ADMIN_API_KEY / REGISTRATION_TOKEN.
5. docker compose up -d --build
6. Verify:
     curl -sS http://127.0.0.1:9000/api/health | jq .
     curl -sS https://registry.shogun-os.ai/api/health | jq .
     curl -sS -X POST https://registry.shogun-os.ai/api/install/bootstrap \
       -H 'Content-Type: application/json' \
       -d '{"email":"smoke@shogun-os.ai","installer_version":"update"}' | jq .
   Expect install_token starting with inst_
7. Report health + bootstrap success (fingerprints only).

Runbook detail: https://raw.githubusercontent.com/limcheehow/shogun-os/main/docs/architecture/SEAMLESS_INSTALL.md
```

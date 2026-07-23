# Security Policy

## Threat Model

Shogun OS is designed for an organization where multiple department agents share the same infrastructure but must not access each other's data. The primary threat is **cross-department data leakage** through shared infrastructure.

## Trust Boundaries

### Profile Isolation (Hard Boundary)

Each Hermes Agent profile is a **hard security boundary**:

| Attack Vector | Mitigation |
|--------------|------------|
| Profile A reads Profile B's config | Separate directories under `~/.hermes/profiles/` — no cross-reads by default |
| Profile A reads Profile B's memory | Each profile has its own memory store — no cross-writes |
| Profile A reads Profile B's cron jobs | Cron jobs are scoped to their creating profile |
| Profile A reads Profile B's Slack DMs | Separate Slack bot tokens — each bot only sees its own conversations |
| Profile A queries Profile B's gbrain data | gbrain source isolation — Profile A can only query `shared/` + its own source |

### Slack Bot Isolation

**Critical:** Each department MUST have its own Slack bot. A single bot serving all departments would:
- Allow any department agent to read all Slack channels
- Expose cross-department conversations to the wrong agent
- Break the principle of least privilege

Each Slack bot requires:
- Its own **Slack App** (created in api.slack.com)
- Its own **Bot User OAuth Token** (xoxb-...)
- Its own **App-Level Token** (xapp-...)
- Its own **bot user** (invited only to its department's channels)

### GBrain Source Isolation

Knowledge is segmented by gbrain source:

```
shared/  ← All profiles can READ (federated)
hr/      ← Only HR profile can WRITE
finance/  ← Only Finance profile can WRITE
...       ← Each department has one write source
```

Federated read is **read-only** from `shared/`. Profiles cannot accidentally write to another department's source because each profile's `mcp_servers.gbrain.env.GBRAIN_SOURCE` is set to its own source.

### Secret Management

| Secret | Location | Protection |
|--------|----------|------------|
| LLM API keys | `~/.hermes/.env` or profile `.env` | File permissions 600; NEVER committed to git |
| Google DWD SA key | `~/.hermes/secrets/google-dwd-sa.json` | File permissions 600; NEVER committed |
| Slack bot tokens | Profile `.env` | NEVER committed |
| Supabase keys | `~/.hermes/.env` | NEVER committed |
| Profile upload keys | `~/.hermes/auth.json` | NEVER committed |

## Operational Security

### During Install

1. Clone the repo — verify via HTTPS from `github.com/limcheehow/shogun-os`
2. Inspect any script before running with `sudo` — shogun-os scripts use `sudo` only for systemd service installation
3. Do NOT run as root — use the user's primary account

### During Operation

1. Never share profile passwords or Slack tokens via unencrypted channels
2. Rotate tokens if a profile is compromised
3. Audit `~/.hermes/cron/jobs.json` periodically — each cron job has a `deliver` field showing where its output goes
4. Check `~/.hermes/logs/gateway.log` for unauthorized access attempts

### Reporting a Vulnerability

If you find a security issue in Shogun OS, please open a GitHub issue with the `security` label. Do NOT disclose via public channels.

## Security Checklist

Before deploying to production:

- [ ] Each department has its own Slack bot with unique tokens
- [ ] Google DWD scopes are limited to what each recipe needs (not all scopes for all profiles)
- [ ] `.env` files are 600 permissions and never in git
- [ ] Supabase database has row-level security enabled
- [ ] Gateway webhook secret is set (auto-generated on install)
- [ ] `shared/` gbrain source contains only non-sensitive data (no salaries, no private notes)
- [ ] Each profile's `allowed_channels` is scoped to its own Slack channels
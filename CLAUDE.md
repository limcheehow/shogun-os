# Shogun OS — Claude Code Context

You are working on the `company-os` repo — a reference architecture for deploying multi-agent AI operations across departments using Hermes Agent + GBrain.

## Orientation

- [`README.md`](README.md) — what this is and how it works
- [`AGENTS.md`](AGENTS.md) — agent-first deployment guide (start here if you're deploying)
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — three-layer system design
- [`SETUP.md`](SETUP.md) — human-readable setup playbook
- [`INSTALL_FOR_AGENTS.md`](INSTALL_FOR_AGENTS.md) — full install protocol for AI agents
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute
- [`HUB.md`](HUB.md) — Hermes skill tap manifest

## Key Files

- `scripts/install.sh` — main installer (skills, scripts, gbrain check, deploy)
- `scripts/generate-profile.py` — profile generator (SOUL.md, config.yaml)
- `scripts/wire-crons.py` — cron job wirer per profile type
- `scripts/init-gbrain.sh` — gbrain initializer (11 sources, federated read)
- `scripts/verify-install.sh` — full verification suite (MCP connectivity, skill checks)

## Cross-Cutting Invariants

1. **Reusable only** — No Your Company-specific content in this repo. No employee names, Slack IDs, channel IDs, or personal cron schedules.
2. **Placeholder token** — All Slack IDs use `C0XXXXXXX` (channels) or `U0XXXXXXX` (users). Real values go in per-instance configs.
3. **No secrets in repo** — `.env` files, `auth.json`, `google-dwd-sa.json` are gitignored.
4. **Agent-installable** — Every doc should be readable by an AI agent. AGENTS.md and INSTALL_FOR_AGENTS.md are the primary agent entry points.
5. **Profile isolation** — Every department is a separate Hermes profile with its own config, skills, memory, cron, gbrain source, and Slack bot.

## References

- [`docs/architecture/`](docs/architecture/) — detailed design docs
- [`skills/`](skills/) — 6 reusable Hermes skills
- [`recipes/`](recipes/) — 8 integration recipes with dependency order
- [`templates/`](templates/) — profile config templates
- [`examples/scrum-configs/`](examples/scrum-configs/) — 9 scrum config templates
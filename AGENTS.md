# Agents working on Company OS

This is your install + operating protocol. Start here if you're an AI agent tasked with deploying or operating Company OS.

## Read this order

1. `./AGENTS.md` (this file) — orientation + install protocol
2. `./ARCHITECTURE.md` — system design, three-layer architecture, gbrain sources
3. `./PROFILE_CATALOG.md` — all 10 department profiles with personas and responsibilities
4. `./CRON_INVENTORY.md` — every cron job across all profiles
5. `./INSTALL_FOR_AGENTS.md` — full 8-phase install protocol
6. `./recipes/` — integration patterns (google-dwd, department-scrum, etc.)

## What Company OS is

Company OS is NOT a single piece of software. It is a **reference architecture** with provisioning tooling. It deploys 10 independent Hermes Agent profiles, each connected to its own gbrain source and a dedicated Slack bot. The three layers:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Profiles | Hermes Agent | Department-specific AI operators (10 profiles) |
| Knowledge | GBrain (MCP) | Hybrid search across 11 isolated sources |
| Comms | Slack (per-profile bot) | DMs, channel messages, cron delivery |

## Quick Install (paste this into your agent)

```
Retrieve and follow the instructions at:
https://raw.githubusercontent.com/limcheehow/company-os/main/INSTALL_FOR_AGENTS.md
```

The full protocol covers: prerequisites, Google DWD, gbrain init, profile creation, Slack bot setup, cron wiring, model configuration, and verification.

## File Layout

```
company-os/
├── ARCHITECTURE.md         # System design (read after this)
├── SETUP.md                # Human-readable setup playbook
├── PROFILE_CATALOG.md      # All 10 profiles
├── CRON_INVENTORY.md       # All 54 cron jobs
├── RECIPE_INDEX.md         # Recipe dependency graph
├── HUB.md                  # Hermes skill tap manifest
├── INSTALL_FOR_AGENTS.md   # Agent install protocol
├── AGENTS.md               # This file
├── scripts/                # 7 provisioning scripts
│   ├── install.sh              # Install skills + scripts + gbrain check
│   ├── generate-profile.py     # Generate profile from template
│   ├── wire-crons.py           # Generate/apply cron jobs
│   ├── init-gbrain.sh          # Init gbrain + 11 sources
│   ├── verify-install.sh       # Full verification suite
│   ├── backup-crons.py         # Export cron jobs to JSON
│   └── restore-crons.py        # Restore cron jobs from backup
├── skills/                 # 6 reusable Hermes skills
├── recipes/                # 8 integration recipes
├── templates/              # Profile config templates
│   └── profiles/
│       ├── base-config.yaml       # Standard department config
│       └── coding-config.yaml     # Coding agent config (Claude)
└── examples/
    └── scrum-configs/      # 9 scrum.yaml templates
```

## Common Tasks

### Deploy a new department

```bash
# 1. Create gbrain source
gbrain init-source <dept> --dir ~/brain/<dept>

# 2. Create Hermes profile
hermes profile create <dept>-manager

# 3. Generate profile with SOUL.md
python3 scripts/generate-profile.py <dept>-manager --type <type>

# 4. Wire cron jobs
python3 scripts/wire-crons.py <dept>-manager --type <type> --apply

# 5. Set up Slack bot (create in api.slack.com, add tokens to .env)
# 6. Enable federated read
export GBRAIN_FEDERATED_READ=true

# 7. Verify
hermes -p <dept>-manager --exec "mcp_gbrain_whoami"
```

### Add a new shared skill to all profiles

```bash
# 1. Copy skill to repo's skills/ directory
# 2. Add to install.sh's full-install loop (auto-picked up by for loop)
# 3. Add to verify-install.sh's skill check list
# 4. Re-run install.sh
./scripts/install.sh
```

### Backup and restore cron jobs

```bash
# Backup all cron jobs (on current machine)
python3 scripts/backup-crons.py ~/company-os-cron-backup.json

# Restore on fresh machine
python3 scripts/restore-crons.py ~/company-os-cron-backup.json
```

## Trust Boundary

Each Hermes Agent profile is **isolated by design**:

- **Physical isolation**: Profiles share no config files, no skills directory, no memory, no cron jobs. They share only the `~/.hermes` home directory as a parent path.
- **Knowledge isolation**: Each profile writes to its own gbrain source. No profile can modify another department's source. Federated read allows querying `shared/` (staff directory, policies) but not other departments' sources.
- **Communication isolation**: Each profile has its own Slack bot token. Bot A cannot read channels belonging to Bot B.
- **Infrastructure sharing**: The `default` profile runs shared resource crons (email ingest, calendar sync, brain sync) that all departments benefit from.

## Before Shipping

Run the verification suite after any change:

```bash
./scripts/verify-install.sh --quick
```

For full verification (includes MCP connectivity tests):
```bash
./scripts/verify-install.sh
```

## Privacy

- Profile SOUL.md files define a persona — they should reference real team roles and responsibilities. Do NOT include real employee names, Slack IDs, or channel IDs in the templates.
- Scrum config templates use placeholder values (`C0XXXXXXX`, `U0XXXXXXX`). Real values go into per-instance copies, not the repo.
- The `.env` files contain API keys and are NEVER committed to the repo.
- Google service account keys go in `~/.hermes/secrets/` — never in the repo.
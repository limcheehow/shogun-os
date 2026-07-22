# Contributing to Shogun OS

## What This Repo Is

Shogun OS is a **reference architecture** — not a shipped product. Contributions that make the architecture more reusable, better documented, or easier to deploy are welcome. Contributions that add Your Company-specific content belong in your own fork or in the running Hermes profiles, not here.

## What Goes In

- **Reusable skills** — Hermes skills that any company can use (scrum, brain compliance, formatting, etc.)
- **Provisioning scripts** — tools that automate deployment
- **Recipe integrations** — documented patterns for connecting external services
- **Architecture docs** — anything that helps someone understand or deploy the system
- **Bug fixes** — broken links, dead references, script errors

## What Stays Out

- **Personal/Your Company-specific content** — no specific employee names, Slack IDs, channel IDs, or company-specific cron schedules
- **Personal skills** — trading scanners, budget trackers, meal planners, personal fitness
- **API keys or secrets** — never, ever
- **Binary files** — no images, no compiled artifacts

## Repository Structure

```
shogun-os/
├── scripts/              # Bash/Python provisioning scripts
├── skills/               # Reusable Hermes skills (SKILL.md format)
├── recipes/              # Integration recipes (gbrain-recipe format)
├── templates/            # Profile config templates
│   └── profiles/         # base-config.yaml, coding-config.yaml
├── examples/
│   └── scrum-configs/    # Scrum config templates (placeholders only)
├── docs/                 # Architecture docs
├── ARCHITECTURE.md       # System design (root-level copy)
├── SETUP.md              # Human setup playbook
├── PROFILE_CATALOG.md    # All 10 profiles
├── CRON_INVENTORY.md     # All 54 cron jobs
├── RECIPE_INDEX.md       # Recipe dependency graph
├── AGENTS.md             # Agent-first deployment guide
├── INSTALL_FOR_AGENTS.md # Full agent install protocol
├── HUB.md                # Hermes skill tap manifest
└── README.md             # This is where people start
```

## Skill Format

Skills follow the Hermes SKILL.md convention:

```markdown
---
name: my-skill
description: "What this skill does"
version: 1.0.0
triggers:
  - "keyword that loads this skill"
---

# My Skill

## Workflow

Step-by-step instructions...

## Pitfalls

Known issues and workarounds...
```

## Testing

```bash
# Verify install scripts
./scripts/verify-install.sh --quick

# Lint Python scripts
python3 -m py_compile scripts/*.py

# Validate YAML templates
python3 -c "import yaml; yaml.safe_load(open('templates/profiles/base-config.yaml'))"
```

## PR Workflow

1. Open an issue describing the change
2. Fork the repo, make your changes
3. Run `verify-install.sh --quick` to verify
4. Submit a PR with a clear description of what changed and why

## Adding a New Skill

1. Create `skills/<name>/SKILL.md` with frontmatter + body
2. Add to `scripts/install.sh`'s full-install loop (auto-picked by the `for` loop)
3. Add to `scripts/verify-install.sh`'s skill check list
4. Add to `HUB.md` skill table
5. Document in `RECIPE_INDEX.md` if it's a dependency for other skills

## Adding a New Profile Type

1. Add entry to `scripts/generate-profile.py`'s `PROFILE_META` dict
2. Add SOUL snippet to `SOUL_SNIPPETS` dict
3. Add cron definitions to `scripts/wire-crons.py`'s `PROFILE_EXTRA_CRONS` if needed
4. Add scrum config template to `examples/scrum-configs/`
5. Document in `PROFILE_CATALOG.md`
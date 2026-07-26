---
id: shogunify
name: Shogunify
version: 1.0.0
description: >
  Agent-facing questionnaire to add skills, connectors, workflows, and
  profiles that are Hermes-profile-aware and gbrain-compliant. Slash: /shogunify.
category: architecture
setup_time: 5 min
cost: $0
depends_on: []
---

# Shogunify

> **Structured authoring for Shogun OS** — like gbrain skillify, but for
> Hermes skills, provider integrations, crons, and department profiles.
> Everything is **profile-scoped**: write to the wrong Hermes home and the
> slash command or cron never shows up.

## Quick start

```bash
# After install (or after pulling this skill)
python3 skills/shogunify/scripts/install-to-profiles.py \
  --skill shogunify --profiles all --force

# In any Hermes session (CLI / Telegram / Slack)
/shogunify
/shogunify skill my-skill for hr-manager
/shogunify integration VendorName domain accounting profile finance-manager
```

Hermes auto-registers installed skills as slash commands: skill name
`shogunify` → **`/shogunify`**.

## Why it exists

| Before | After |
|--------|--------|
| Human guide only (`creating-provider-abstractions.md`) | Agent questionnaire → files |
| Skills dropped in `~/.hermes/skills/` only | Explicit owning profile + multi-profile install |
| Ad-hoc INDEX updates | Checklist for HUB / RECIPE_INDEX / generate-profile / verify |
| Easy to leak secrets into git | Path map + compliance checklist |

## Modes

| Mode | Produces |
|------|----------|
| **skill** | `SKILL.md` (+ scripts/refs) under repo and/or profile `skills/` |
| **integration** | New domain: `CONTRACT` + `GENERIC_SKILL` + bridge + provider |
| **provider-only** | Plugin + provider doc against existing CONTRACT |
| **workflow** | Profile-scoped cron (`hermes -p <profile> cron …`) |
| **profile** | Wraps `generate-profile.py` + gbrain source + skill links |

Questionnaires live in `skills/shogunify/references/questionnaire-*.md`.

## Profile path rules (non-negotiable)

| Target | Path |
|--------|------|
| Default profile skill | `~/.hermes/skills/<name>/` |
| Named profile skill | `~/.hermes/profiles/<profile>/skills/<name>/` |
| Profile secrets | `~/.hermes/profiles/<profile>/.env` |
| Profile MCP | `~/.hermes/profiles/<profile>/config.yaml` |
| Cron | **must** use `hermes -p <profile> cron …` |
| Shared meta-skills | Install default **and** symlink into each profile |

Full map: [`skills/shogunify/references/path-map.md`](../../skills/shogunify/references/path-map.md).

## Install / ship

### Repo layout

```
skills/shogunify/
├── SKILL.md
├── references/
│   ├── path-map.md
│   ├── questionnaire-integration.md
│   ├── questionnaire-skill.md
│   ├── questionnaire-workflow.md
│   ├── questionnaire-profile.md
│   └── compliance-checklist.md
├── templates/
│   ├── skill-SKILL.md.tpl
│   ├── contract.md.tpl
│   ├── generic-skill.md.tpl
│   └── provider.md.tpl
└── scripts/
    ├── install-to-profiles.py
    └── e2e_test_shogunify.py
```

### Wire into a machine

```bash
# 1. Full install picks up skills/shogunify via install.sh loop
./scripts/install.sh

# 2. Ensure every named profile has the slash command
python3 skills/shogunify/scripts/install-to-profiles.py \
  --skill shogunify --profiles all --force

# 3. New profiles get it automatically (SHARED_PROFILE_SKILLS)
python3 scripts/generate-profile.py demo --type base --dry-run
# → Skills: ['company-workflow', 'shogunify', ...]
```

`install.sh --profile <name>` also installs `company-workflow`, **`shogunify`**, and `department-scrum` into that profile’s skill home.

## Relationship to provider-abstraction guide

- **Human deep dive:** [`creating-provider-abstractions.md`](creating-provider-abstractions.md)
- **Agent entrypoint:** `/shogunify` → integration / provider-only mode
- Prefer Shogunify for day-to-day scaffolding; keep the long guide for edge cases (OAuth cache layout, importlib pitfalls).

## E2E tests

```bash
python3 skills/shogunify/scripts/e2e_test_shogunify.py
# optional: --keep  leaves profiles/test-shogunify for inspection
```

Coverage:

1. Source + generate-profile shared wiring  
2. Install to default + all named profiles  
3. Disposable `test-shogunify` profile  
4. Scaffold demo skill + demo connector templates  
5. Hermes skill list / slash registration (`/shogunify`, `/demo-echo-skill`)  
6. Path isolation (no leak to other profiles)

## Compliance

Before calling done, run through  
[`skills/shogunify/references/compliance-checklist.md`](../../skills/shogunify/references/compliance-checklist.md):

- SKILL frontmatter (`name`, `description`)
- Correct Hermes home for owning profile
- Indexes: `HUB.md`, `RECIPE_INDEX.md`, `CRON_INVENTORY.md`, `PROFILE_CATALOG.md` as applicable
- `generate-profile.py` / `verify-install.sh` updates when shipping shared skills
- No secrets in git; MCP `env:` lists every var the bridge reads

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/shogunify` missing on a bot | Skill not under that profile’s `skills/`; re-run `install-to-profiles.py --profiles <name> --force` |
| Cron never fires | Job created without `-p <profile>` |
| MCP tools empty | Keys only in main `.env`; copy to profile `.env` + config `env:` |
| Gateway still old slash menu | Restart gateway / new session |

## See also

- Skill body: [`skills/shogunify/SKILL.md`](../../skills/shogunify/SKILL.md)
- Provider guide: [`creating-provider-abstractions.md`](creating-provider-abstractions.md)
- Hub row: [`HUB.md`](../../HUB.md)
- Recipe index: [`RECIPE_INDEX.md`](../../RECIPE_INDEX.md)

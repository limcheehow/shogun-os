---
name: shogunify
description: "Use when adding a Shogun OS integration, skill, workflow/cron, or connector — structured questionnaire that produces gbrain-compliant + Hermes-profile-aware artifacts. Slash: /shogunify."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [shogun, skillify, questionnaire, connector, recipe, workflow, profile]
    category: devops
    related_skills: [company-workflow, profile-management, hermes-agent-skill-authoring, brain-compliance]
---

# Shogunify — Structured Authoring for Shogun OS

**Slash command:** `/shogunify` (skill name = command; works CLI + Telegram + Slack once installed on the active profile).

Turn a vague "add X" request into correctly placed, Shogun-compliant + gbrain-compliant artifacts. Every skill, connector, and cron is **profile-owned** — write to the right Hermes home or the artifact is invisible to that profile.

## When to Use

- User runs `/shogunify` or says "shogunify …"
- Adding a **connector / provider** (API, MCP bridge, plugin)
- Adding a **skill** (`SKILL.md` + optional scripts/references)
- Adding a **workflow / cron** for a department profile
- Extending an existing domain CONTRACT with a new provider
- User asks "how do I add this to Shogun OS properly?"

**Don't use for:** one-off ops that aren't reusable (use normal tools). Pure code bugs → `company-workflow` / `systematic-debugging`.

## Hard Rule — Profile Paths First

Before writing ANY file, resolve **active profile** and **target profile** (they may differ).

```bash
# Active Hermes home for THIS session
echo "HERMES_HOME=${HERMES_HOME:-$HOME/.hermes}"
# Named profiles
ls "$HOME/.hermes/profiles/"
# Confirm skill would be visible as slash command for a profile
test -f "${HERMES_HOME:-$HOME/.hermes}/skills/shogunify/SKILL.md" && echo OK
```

| Target | Path (MUST use) |
|--------|-----------------|
| Default profile skill | `~/.hermes/skills/<name>/` |
| Named profile skill | `~/.hermes/profiles/<profile>/skills/<name>/` |
| Profile config / MCP | `~/.hermes/profiles/<profile>/config.yaml` |
| Profile secrets | `~/.hermes/profiles/<profile>/.env` (never main `.env`) |
| Profile cron | `hermes -p <profile> cron …` → that profile's `cron/jobs.json` |
| Profile SOUL | `~/.hermes/profiles/<profile>/SOUL.md` |
| Profile memory | `~/.hermes/profiles/<profile>/memories/` |
| Shared bridge scripts | `~/.hermes/scripts/` (or profile `scripts/` if isolated) |
| Shogun repo source of truth | `~/shogun-os/` (skills/, recipes/, templates/, HUB.md, …) |
| Gbrain source for dept | page under that dept source; `GBRAIN_SOURCE` in profile `.env` |

Full map: `references/path-map.md`.

**Never** edit another profile's `skills/`, `plugins/`, `cron/`, or `memories/` unless the user explicitly names that profile. Profiles do **not** inherit main `~/.hermes/.env` or main skills unless you symlink/install into that profile.

## Protocol (every /shogunify run)

### 0. Intent + profile

Ask (or infer from args):

1. **Mode:** `integration` | `skill` | `workflow` | `provider-only` | `profile`  
   - Args shortcut: `/shogunify skill leave-balance for hr-manager`
2. **Owning profile:** e.g. `hr-manager`, `finance-manager`, `default`, or `shared` (install to all)
3. **Also ship to repo?** Default **yes** for reusable Shogun assets → write under `~/shogun-os/` then install into Hermes homes.

Completion: mode + profile confirmed; path-map loaded if needed.

### 1. Interview

Load the matching questionnaire and ask **only unanswered** questions (skip what user already provided). Prefer `clarify` for multi-choice.

| Mode | Reference |
|------|-----------|
| integration (new domain or connector) | `references/questionnaire-integration.md` |
| provider-only (existing CONTRACT) | same file, "Provider-only branch" |
| skill | `references/questionnaire-skill.md` |
| workflow / cron | `references/questionnaire-workflow.md` |
| profile (new dept agent) | `references/questionnaire-profile.md` |

### 2. Reuse check

Before scaffolding:

- Domain CONTRACT already in `~/shogun-os/recipes/<domain>/CONTRACT.md`? → provider-only path
- Skill name clash: `find ~/.hermes/skills ~/.hermes/profiles -name SKILL.md | xargs grep -l "^name: <name>"`
- Profile exists: `test -d ~/.hermes/profiles/<name>`
- Cron name unique for that profile

### 3. Generate

Use templates under `templates/`. Write files in this order:

1. **Repo** (`~/shogun-os/…`) if shipping shared asset  
2. **Install / link** into the correct Hermes skill dir(s)  
3. **Profile wiring** (`config.yaml` MCP, `.env` keys, SOUL skill list, cron)  
4. **Indexes** (only if repo ship): `HUB.md`, `RECIPE_INDEX.md`, `CRON_INVENTORY.md`, `PROFILE_CATALOG.md`, `scripts/generate-profile.py`, `scripts/install.sh`, `scripts/verify-install.sh`

Exact checklists: `references/compliance-checklist.md`.

### 4. Install to profile(s)

```bash
# Preferred: installer copies skill into default HERMES_HOME
# Then symlink into each named profile that should expose /shogunify or the new skill:
python3 ~/shogun-os/skills/shogunify/scripts/install-to-profiles.py --skill <name> --profiles <p1,p2|all-shogun>
```

For **shogunify itself** (shared meta-skill on every profile):

```bash
python3 ~/shogun-os/skills/shogunify/scripts/install-to-profiles.py --skill shogunify --profiles all
```

### 5. Verify

- [ ] `SKILL.md` frontmatter: `name` + `description` (≤1024), starts with `---`
- [ ] Artifact visible under **owning profile's** `skills/` (or default home)
- [ ] Slash: new session on that profile → `/commands` or try `/<skill-name>`
- [ ] MCP tools listed if connector (`hermes -p <profile> mcp list` / tools)
- [ ] Cron listed: `hermes -p <profile> cron list` if workflow
- [ ] Gbrain pages (if any) pass brain-compliance frontmatter
- [ ] No secrets committed to `~/shogun-os/`

### 6. Report

Return a short table: mode, profile, files created/updated, install status, how to invoke (`/name` + natural language), remaining manual steps (API keys, Slack scopes, gateway restart).

## Slash usage

```
/shogunify
/shogunify skill <name> for <profile>
/shogunify integration <vendor> domain <domain> profile <profile>
/shogunify workflow <name> on <profile>
/shogunify provider <vendor> for <domain>
/shogunify profile <name> type <type>
```

Bare `/shogunify` → start Step 0 interview.

## Modes (one-line)

| Mode | Produces |
|------|----------|
| **integration** | `recipes/<domain>/` CONTRACT + GENERIC_SKILL + bridge/plugin + provider doc + profile MCP |
| **provider-only** | `plugins/<vendor>.py` + `providers/<vendor>.md` + env docs (no CONTRACT change) |
| **skill** | `skills/<cat>/<name>/SKILL.md` (+ scripts/refs) + profile install + HUB |
| **workflow** | Cron on **that profile** + optional `~/.hermes/scripts/*.py` + CRON_INVENTORY |
| **profile** | `generate-profile.py` path: SOUL, config, gbrain source, skill links, scrum crons |

Provider abstraction deep dive (existing guide): `~/shogun-os/docs/recipes/creating-provider-abstractions.md`.

## Common Pitfalls

1. **Wrote skill only to `~/.hermes/skills/`** — named profiles won't see `/shogunify` or the new skill until linked into `profiles/<name>/skills/`.
2. **Cron created without `-p <profile>`** — job lands on wrong profile's scheduler.
3. **MCP env in main `.env` only** — profile subprocess gets empty vars; put keys in profile `.env` AND list them in that profile's `config.yaml` `mcp_servers.*.env`.
4. **Edited another profile by accident** — always print target path before write.
5. **Provider-specific tool names in GENERIC_SKILL** — only CONTRACT names (`acct_*`, `tt_*`, …).
6. **Forgot index updates** — HUB / RECIPE_INDEX / generate-profile skills list / verify-install.
7. **Gateway not restarted** after config.yaml / skill install — slash menu and MCP won't refresh.
8. **Secrets in repo** — credentials only in profile `.env` / `~/.hermes/secrets/`.
9. **New domain without prefix + profile owner** — every CONTRACT needs `<prefix>_` and a home profile.
10. **Assuming `install.sh` updates named profiles** — full install hits default `HERMES_HOME/skills/`; named profiles need `install-to-profiles.py` or `generate-profile.py` link step.

## Verification Checklist

- [ ] Mode + owning profile stated
- [ ] Path-map followed for every write
- [ ] Questionnaire answers captured (or skipped with reason)
- [ ] Reuse check done
- [ ] Artifacts generated from templates
- [ ] Installed into correct profile skill dir(s)
- [ ] Indexes updated if repo-shipped
- [ ] Smoke verify passed
- [ ] User told how to invoke + any manual key/restart steps

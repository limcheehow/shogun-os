# Hermes + Shogun Path Map

Hermes is **profile-scoped**. `HERMES_HOME` for the default profile is `~/.hermes`. For a named profile it is effectively `~/.hermes/profiles/<name>/` (config, skills, cron, memory, .env).

## Resolve target before writing

| Question | How to answer |
|----------|----------------|
| Which profile am I running as? | `echo $HERMES_HOME` / `/profile` slash / session banner |
| Where should a new skill live for profile P? | If P is default → `~/.hermes/skills/<skill>/`. Else → `~/.hermes/profiles/P/skills/<skill>/` |
| Shared meta-skill on all profiles? | Install under `~/.hermes/skills/<skill>/` **and** symlink into each `profiles/*/skills/<skill>` |
| Source of truth for Shogun shipping? | `~/shogun-os/` then install/copy/symlink into Hermes homes |

## Directory map

### Default profile (`~/.hermes/`)

| Artifact | Path |
|----------|------|
| Skills | `skills/<name>/SKILL.md` |
| Scripts (cron no_agent) | `scripts/<file>.py` or `.sh` |
| Cron jobs | `cron/jobs.json` |
| Config | `config.yaml` |
| Secrets | `.env` |
| Plugins | `plugins/<name>/` |
| Memory | `memories/` |
| Sessions | `sessions/` |
| Gateway logs | `logs/gateway.log` |
| MCP OAuth cache | `mcp-tokens/` |
| Recipes (installed copy) | `recipes/` (from install.sh) |
| Templates | `templates/` |

### Named profile (`~/.hermes/profiles/<profile>/`)

Same layout **inside the profile directory**. Does **not** inherit parent `.env` or parent skills unless symlinked.

| Artifact | Path |
|----------|------|
| Skills | `skills/<name>/` (often symlink → `~/.hermes/skills/<name>` or repo) |
| Config | `config.yaml` — MCP servers, channel_prompts, models |
| Secrets | `.env` — API keys for this bot only |
| Cron | `cron/jobs.json` — only this profile's scheduler |
| SOUL | `SOUL.md` |
| Memory | `memories/` |
| Gateway port marker | `.gateway-port` |

### Shogun OS repo (`~/shogun-os/`)

| Artifact | Path |
|----------|------|
| Shared skills | `skills/<name>/` or `skills/<category>/<name>/` |
| Provider abstractions | `recipes/<domain>/{CONTRACT,GENERIC_SKILL}.md`, `bridges/`, `plugins/`, `providers/` |
| Classic recipes | `recipes/<name>.md` |
| Profile templates | `templates/profiles/*.yaml` |
| Profile generator | `scripts/generate-profile.py` |
| Installer | `scripts/install.sh` |
| Verify | `scripts/verify-install.sh` |
| Skill tap list | `HUB.md` |
| Recipe graph | `RECIPE_INDEX.md` |
| Cron catalog | `CRON_INVENTORY.md` |
| Profile catalog | `PROFILE_CATALOG.md` |
| Provider guide | `docs/recipes/creating-provider-abstractions.md` |

### Gbrain

| Artifact | Path / rule |
|----------|-------------|
| Dept write source | `GBRAIN_SOURCE` in profile `.env` (e.g. `hr`, `finance`) |
| Shared read | `shared` source when `GBRAIN_FEDERATED_READ=true` |
| Page types / frontmatter | active schema pack; use `brain-compliance` skill |
| Never | Write hr pages from finance profile without explicit user override |

## Profile → domain ownership (shared depts)

| Profile | Gateway (default) | Provider recipe | Tool prefix |
|---------|-------------------|-----------------|-------------|
| hr-manager | 9101 | `recipes/hr/time-tracking/` | `tt_` |
| finance-manager | 9102 | `recipes/accounting/` | `acct_` |
| procurement-manager | 9103 | `recipes/procurement/` | `proc_` |
| crm-manager | 9104 | `recipes/crm/` | `crm_` |
| marketing-manager | 9105 | `recipes/marketing/` | `mkt_` |
| compliance-manager | 9106 | `recipes/compliance/` | `comp_` |
| customer-support | 9107 | `recipes/support/` | `spt_` |
| project-manager | 9108 | `recipes/projects/` | `proj_` |
| product-manager | 9109 | `recipes/product/` | `pd_` |
| coding-agent | 9110 | `recipes/engineering/` | `eng_` |
| default | infra | brain-ingest, drive, token | — |

## Install patterns Hermes understands

1. **Copy into profile skills dir** — self-contained; updates require re-copy.
2. **Symlink profile skill → `~/.hermes/skills/<name>`** — one install, many profiles (preferred for shogunify + shared skills).
3. **Symlink profile skill → `~/shogun-os/skills/<name>`** — what `generate-profile.py` does for repo skills; good for dev machines with repo checkout.
4. **`skills.external_dirs`** in config — optional scan roots; prefer explicit profile skills for predictability.

## Commands that must include profile

```bash
hermes -p hr-manager cron create ...
hermes -p finance-manager mcp list
hermes -p crm-manager config set ...
# Gateway for a dedicated bot profile
hermes gateway run --profile hr-manager   # only if that profile owns tokens
```

Main gateway + channel routing: skills still load from the **session profile** Hermes resolved for that chat — wrong skills dir = missing `/command`.

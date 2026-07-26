# Shogunify Compliance Checklist

## Gbrain / skill frontmatter

- [ ] `SKILL.md` begins with `---` at byte 0  
- [ ] `name` + `description` present; description ≤ 1024  
- [ ] Body non-empty after frontmatter  
- [ ] Brain pages (if any): valid YAML frontmatter, correct `type`, schema pack prefixes  
- [ ] No secrets in markdown committed to git  

## Shogun naming

- [ ] Skill/recipe names kebab-case  
- [ ] Domain tools: `<prefix>_<verb>_<noun>`  
- [ ] GENERIC_SKILL never names a single vendor in tool calls  
- [ ] Profile slugs match PROFILE_CATALOG / generate-profile  

## Hermes profile placement

- [ ] Skill installed under **owning** profile `skills/` (or default home)  
- [ ] Shared skills symlinked to all intended profiles  
- [ ] Cron created with `hermes -p <profile>`  
- [ ] MCP `env:` block lists every var the provider reads  
- [ ] Keys live in **profile** `.env`, not only main `.env`  
- [ ] SOUL.md skill list updated if persona should advertise capability  

## Repo shipping (when applicable)

- [ ] Files under `~/shogun-os/`  
- [ ] `HUB.md` skill row  
- [ ] `RECIPE_INDEX.md` for connectors  
- [ ] `CRON_INVENTORY.md` for crons  
- [ ] `PROFILE_CATALOG.md` for profiles  
- [ ] `scripts/generate-profile.py` skills list  
- [ ] `scripts/verify-install.sh` check  
- [ ] `docs/recipes/creating-provider-abstractions.md` only if pattern change  

## Post-install

- [ ] New session or gateway restart so slash commands refresh  
- [ ] Smoke: `/skill-name` or tool call  
- [ ] Report remaining manual steps to user  

# Questionnaire — Skill

Use for Hermes `SKILL.md` packages (agent procedures), not raw MCP contracts.

## Entry

Confirm: **mode=skill**, **skill name** (kebab-case), **owning profile** or `shared`/`all`.

## Questions

1. **Name?** lowercase hyphens, ≤64 chars  
2. **Description?** trigger-focused, ≤1024 chars, prefer "Use when …"  
3. **Category / folder?**  
   - Shogun repo: top-level under `skills/` or `skills/<category>/`  
   - Match existing peers when possible  
4. **Owning profile(s)?**  
   - one profile | list | all Shogun dept profiles | default only  
5. **Triggers** (phrases / slash intent)  
6. **Tools required:** terminal | file | web | browser | mcp(which) | delegation | vision | memory | cronjob  
7. **Workflows:** 3–10 named procedures with steps + completion criteria  
8. **Prerequisites:** env vars, MCP servers, other skills, files  
9. **Supporting files?** scripts/ | references/ | templates/  
10. **Cron companion?** if yes → also run workflow questionnaire  
11. **Pitfalls** known now (or "discover during first run")  
12. **Gbrain writes?** if yes: source, page types, frontmatter rules (brain-compliance)  
13. **Ship to repo?** default yes for reusable skills  

## Generation targets

```
# Repo (if shipping)
~/shogun-os/skills/[category/]<name>/
  SKILL.md
  scripts/ ...
  references/ ...
  templates/ ...

# Live Hermes
# default:
~/.hermes/skills/<name>/
# each named owner:
~/.hermes/profiles/<profile>/skills/<name>  → symlink or copy

# Indexes
HUB.md
scripts/install.sh   # full-install already loops skills/*
scripts/verify-install.sh  # add check_skill if core
scripts/generate-profile.py  # add to PROFILE_META[type].skills if profile-default
```

## SKILL.md minimum

- Frontmatter: `name`, `description`, `version`, `metadata.hermes.tags`  
- Body: Overview | When to Use | Procedure | Pitfalls | Verification  
- Description becomes slash-command help text  

## Slash command

Skill `name: foo-bar` → **`/foo-bar`** on every profile that has the skill installed under its skills tree.

## Done when

- [ ] Frontmatter validates  
- [ ] Installed on every owning profile  
- [ ] `/name` works after new session / gateway skill refresh  
- [ ] HUB row if shipped  

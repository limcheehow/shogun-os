# Questionnaire — Workflow / Cron

Use for scheduled jobs and recurring department workflows.

## Entry

Confirm: **mode=workflow**, **owning profile** (required — cron is per-profile).

## Questions

1. **Profile?** (`hr-manager`, `default`, …) — never omit  
2. **Job name?** human-readable, unique on that profile  
3. **Schedule?** `30m` | `every 2h` | `0 9 * * 1-5` | one-shot ISO  
4. **Kind?**  
   - `no_agent` — script stdout is the message (silent if empty)  
   - `agent` — LLM runs prompt each tick  
   - `hybrid` — script collects, agent reasons (`script` + prompt)  
5. **Prompt** (self-contained; no chat context at fire time)  
6. **Skills to load?** ordered list (must exist on that profile)  
7. **Script?** bare filename under that profile's or default `scripts/` only  
8. **Delivery?** origin | local | telegram | slack | platform:chat_id  
9. **Model override?** usually none (avoid pinning free-tier traps)  
10. **Holiday / business-day gate?**  
11. **Update CRON_INVENTORY.md?** default yes if shipping  

## Generation

```bash
# ALWAYS profile-scoped
hermes -p <profile> cron create "<schedule>" \
  --name "<Job Name>" \
  --prompt "..." \
  --skill "skill-a,skill-b" \
  --deliver origin
# optional:
#   --script my-collect.py --no-agent
```

Optional script:

```
~/.hermes/scripts/<name>.py          # if default profile / shared
# or document that profile cron host uses HERMES_HOME/scripts
```

Indexes:

```
~/shogun-os/CRON_INVENTORY.md
skills/<skill>/SKILL.md  # cron template section if skill-owned
```

## Done when

- [ ] `hermes -p <profile> cron list` shows job  
- [ ] Skills referenced exist on that profile  
- [ ] Prompt is self-contained  
- [ ] no_agent scripts stay quiet on empty stdout  
- [ ] Inventory updated if required  

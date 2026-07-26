# Questionnaire — Integration / Connector

Use for new SaaS APIs, MCP bridges, or domain provider abstractions.

## Entry

Confirm: **mode=integration** or **provider-only**, **owning profile**, **vendor name**.

## Questions

### A. Identity

1. **Vendor / system name?** (e.g. Bukku, Shopee, Jibble)
2. **Website / API docs URL?**
3. **One-line purpose?**

### B. Domain placement

4. **Existing domain?**  
   `hr/time-tracking | accounting | procurement | crm | marketing | compliance | support | engineering | projects | product | other`
5. If **other**:  
   - Domain folder name (`recipes/<domain>/`)  
   - Tool prefix (`inv_`, `wms_`, …)  
   - Owning profile slug  
6. **Existing CONTRACT for this domain?** (yes → provider-only branch)

### C. Auth & runtime

7. **Auth:** API key | OAuth2 | HMAC | Basic | custom  
8. **Runtime:** unified MCP bridge + plugin | per-provider bridge | pure skill+CLI (no MCP) | webhook receiver  
9. **Env var names** (list every key the bridge needs)

### D. Operations (CONTRACT tools)

10. **Entities** (Orders, Contacts, …)
11. **P0 tools** (check all that apply):  
    list | get | create | update | delete | search | report | webhook  
12. **For each P0 tool:** name (`prefix_verb_noun`), key input fields, key output fields

### E. Profile wiring

13. **Owning profile(s)** that get the MCP server + GENERIC_SKILL  
14. **Cron jobs?** (schedules + no_agent vs agent)  
15. **SOUL.md mention?** (yes/no — list under Your Skills)

### F. Ship scope

16. **Write to shogun-os repo?** (default yes)  
17. **Also install live Hermes now?** (default yes)

---

## Provider-only branch

Skip CONTRACT + GENERIC_SKILL + bridge skeleton if domain exists.

1. Vendor name  
2. Domain path (`recipes/accounting/`)  
3. Auth + env vars  
4. Confirm plugin implements **same** tool names as CONTRACT  
5. Provider doc path `providers/<vendor>.md`  
6. Update GENERIC_SKILL "Adding a provider" env table if new env keys  
7. Owning profile `.env` + `config.yaml` `env:` block must list **all** keys

---

## Generation targets

### New domain

```
~/shogun-os/recipes/<domain>/
  CONTRACT.md
  GENERIC_SKILL.md
  bridges/<domain>-bridge.py
  plugins/<vendor>.py
  providers/<vendor>.md
  oauth-helper.py          # if OAuth
```

Then:

- `templates/profiles` or profile `config.yaml` → `mcp_servers.<domain>`
- `scripts/generate-profile.py` → skills list includes generic skill name
- `RECIPE_INDEX.md`, `HUB.md`, `PROFILE_CATALOG.md`, `llms.txt` if present
- `scripts/install.sh` `section_recipes` if new top-level dir
- `scripts/verify-install.sh` abstraction check
- Install GENERIC_SKILL into profile skills (name from frontmatter)
- Copy bridge to `~/.hermes/scripts/`

### Provider-only

```
plugins/<vendor>.py
providers/<vendor>.md
+ env docs in GENERIC_SKILL
+ profile .env + mcp env block
```

## Done when

- [ ] CONTRACT tools are provider-agnostic  
- [ ] Plugin returns contract shapes + standard error envelope  
- [ ] Profile MCP config points at installed bridge  
- [ ] `/skill-name` or skill load works on owning profile  
- [ ] No secrets in git  

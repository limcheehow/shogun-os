# Company your-product Profiles — Reference

Full roster of your company's Hermes agent profiles with your-product universe naming. All share the same model (`deepseek-v4-pro` via `custom:dashscope-anthropic`). Channel prompts on the default gateway route Slack/Telegram messages to personas.

| Profile | your-product Name | Meaning | Domain | Slack Channels |
|---|---|---|---|---|
| `default` | Hermes | Messenger god | General assistant | All channels fall through here |
| `product-manager` | — | — | your-product V2 PRDs, Epics, Tasks, Brain | `D0B0LU0HP4L` (Admin DM), `#tech-scrum-updates`, `#sprint-management`, Telegram `-1003882643127` (Company Product) |
| `project-manager` | Taiko (太鼓) | The Drum — sets rhythm | Sprints, resources, milestones, risk | `#sprint-management` |
| `marketing-manager` | Haiku (俳句) | Poetic form — elegant and concise | Content, SEO, social, brand | Telegram `-1003958841816` (Company Marketing) |
| `hr-manager` | Kizuna (絆) | Bonds — human connection | Hiring, onboarding, culture, compliance | — (not yet routed) |
| `procurement-manager` | Kura (蔵) | Storehouse — keeper of resources | Hardware, vendors, licenses, logistics | — (not yet routed) |
| `compliance-manager` | Kata (型) | Prescribed form — standardized practice | ISMS, ISO 27001 docs, policies, audit evidence | — (not yet routed) |
| `finance-manager` | Koku (石) | Wealth measure — feeds the team | Budgets, revenue, burn rate, grants | — (not yet routed) |

## Rename History

- `pm` → `product-manager` on 2026-05-27. The `pm` alias is gone to avoid confusion with project manager. Rename hit a `PermissionError` due to gateway lock — resolved by manual `cp -r` + `rm -rf` (see Pitfalls section in SKILL.md body).

## CLI Aliases

| Profile | Alias | Command |
|---|---|---|
| `product-manager` | `product-manager` | `~/.local/bin/product-manager` |
| `project-manager` | `taiko` | `~/.local/bin/taiko` |
| `hr-manager` | `kizuna` | `~/.local/bin/kizuna` |
| `procurement-manager` | `kura` | `~/.local/bin/kura` |
| `compliance-manager` | `kata` | `~/.local/bin/kata` |
| `finance-manager` | `koku` | `~/.local/bin/koku` |
| `marketing-manager` | `marketing-manager` | `~/.local/bin/marketing-manager` |

## SOUL.md Structure Pattern

Each profile's SOUL.md follows this structure:
1. **Identity** — core principles and mindset
2. **Responsibilities** — numbered list of specific duties
3. **Key Paths** — relevant filesystem paths
4. **Always Load Before Working** — skills to preload
5. **Boundaries** — explicit "do NOT do X" rules
6. **Communication Style** — tone, format, delivery

## Profile Creation Recipe

```bash
# 1. Create the profile
hermes profile create <name>

# 2. Copy config + keys from product-manager
cp ~/.hermes/profiles/product-manager/config.yaml ~/.hermes/profiles/<name>/config.yaml
cp ~/.hermes/profiles/product-manager/.env ~/.hermes/profiles/<name>/.env

# 3. Copy shared memories
cp ~/.hermes/profiles/product-manager/memories/*.md ~/.hermes/profiles/<name>/memories/

# 4. Write SOUL.md persona
write_file ~/.hermes/profiles/<name>/SOUL.md

# 5. Create CLI alias with your-product name
hermes profile alias <name> --name <your-product-name>
```

## Channel Prompt Routing Pattern

The product-manager persona is NOT a separate gateway — it's routed via channel prompts in the **default** gateway config:

```yaml
slack:
  channel_prompts:
    D0B0LU0HP4L: "PRODUCT MANAGER ONLY. ALLOWED: ... BLOCKED: ..."
    C0308PA6Y: "PRODUCT MANAGER ONLY. You are in #tech-scrum-updates..."
    C0ABY3VT4U8: "PRODUCT MANAGER ONLY. You are in #sprint-management..."
```

One gateway, many personas. Profiles define the personality; channel prompts do the routing.
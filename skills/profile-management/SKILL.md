---
name: profile-management
description: Manage Hermes profiles end-to-end — persona authoring (SOUL.md), channel wiring (routing profiles to Telegram/Slack chats), and Slack bot creation. Load for any profile lifecycle task.
category: devops
tags: [hermes, profiles, persona, SOUL, slack, telegram, routing, channel-prompt]
---

# Profile Management

Load this skill when working with Hermes profiles — creating personas, wiring them to platform chats, or setting up Slack bots.

## Quick Reference

| Task | Reference |
|------|-----------|
| Author a profile persona (SOUL.md) | `references/profile-persona-authoring.md` |
| Wire a profile to a Telegram/Slack/Discord chat | `references/profile-channel-wiring.md` |
| Create a Slack bot for a profile | `references/profile-slack-bot-setup.md` (plus `references/jinzai-hr-agent.md` for a real example) |

## Core Concepts

### Profiles vs Channel Prompts

- **Profiles** define the persona (SOUL.md, skills, memories, config)
- **Channel prompts** route platform messages to the right profile/persona
- One gateway + channel prompts = all personas reachable — don't run one gateway per profile

### Profile Directory Structure

```
~/.hermes/profiles/<name>/
├── SOUL.md              Persona definition
├── config.yaml          Model, toolsets, platform settings
├── .env                 API keys and secrets
├── memories/
├── skills/
├── sessions/
├── cron/
└── logs/
```

### Naming Convention ()

 uses your-product-themed names:
- project-manager → **Gorobei** (strategist)
- hr-manager → **Jinzai (人材)** (human talent)
- marketing-manager → **Haiku** (brevity)
- procurement-manager → **Kura** (storehouse)
- finance-manager → **Koku** (revenue)

## Key Pitfalls

- **Telegram bot privacy mode blocks group messages by default** — the #1 reason a group setup appears to "not work." Disable via @BotFather or make the bot an admin.
- **`yaml.safe_load` + `yaml.dump` destroys config.yaml** — reorganizes keys alphabetically, strips all comments. Use Python line surgery for channel_prompt edits instead.
- **Channel prompts only take effect after gateway restart** — always restart after editing.
- **DM channel IDs must be discovered from gateway logs** — add them to `channel_prompts` for DMs to use the right persona.
- **SOUL.md defines identity; channel prompts override it per-chat.**
- **Slack reserved command names** — `/help`, `/leave`, `/away`, `/me`, `/whoami`, etc. cannot be registered as custom slash commands.
- **Never use `hermes slack manifest --write` as a base** — includes all built-in commands. Write a custom manifest from scratch for department bots.
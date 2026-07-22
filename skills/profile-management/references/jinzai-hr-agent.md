# Jinzai HR Agent — Session Reference

Created 2026-06-10. Full workflow from zero to live Slack bot for the hr-manager Hermes profile.

## What Was Built

- **Bot name:** Jinzai (人材) — "Human Talent"
- **Profile:** `~/.hermes/profiles/hr-manager/`
- **Manifest:** `~/.hermes/jinzai-manifest.json`
- **Persona:** Dry humor / self-aware AI / geeky vision AI references
- **Slash commands:** `/shoutout`, `/whosout` (not `/leave` — reserved!), `/policy`, `/jinzai`
- **Access control:** Admin (U02V7GKJ3) = admin view-only; all others = own info only

## Key Steps

1. Wrote custom manifest from scratch (not `hermes slack manifest --write` — too many built-in commands)
2. User created Slack app at api.slack.com via manifest paste
3. Wired tokens to `~/.hermes/profiles/hr-manager/.env`
4. Updated `channel_prompts` in `config.yaml` mapping the DM channel ID discovered from gateway logs
5. Rewrote SOUL.md from "Kizuna" (old persona) to "Jinzai"
6. Started second gateway: `tmux new-session -d -s jinzai-gateway 'hermes --profile hr-manager gateway run'`

## Pitfalls Encountered

- **Reserved commands:** `/help` and `/leave` are Slack built-ins → manifest rejected
- **Duplicate `/new`:** appeared twice in initial manifest → Slack said "duplicated" with no line number
- **SOUL.md vs channel prompt:** old SOUL.md said "You are Kizuna" → bot introduced itself as Kizuna in DMs even after channel prompt was updated
- **DM channel ID:** had to grep gateway logs (`chat=D0...`) to find the user's DM channel ID for the channel prompt
- **Second gateway Telegram conflict:** main @Hermes holds the Telegram token → expected error, ignore for Slack-only bot

## Access Control Rules

Channel prompt and SOUL.md both enforce: Admin = admin (view-only, no edits). Everyone else = own info only. KPI editing explicitly forbidden.
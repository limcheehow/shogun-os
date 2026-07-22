# Company Telegram Group Chat IDs

Known Telegram group chat IDs for your company. Groups are negative integers; DMs are positive.

| Chat ID | Group | Profiles Routed | Bot |
|---|---|---|---|
| `-1003958841816` | Company Marketing | `marketing-manager` (Haiku) | Main Hermes bot |
| `-1003882643127` | Company Product | `product-manager` | Main Hermes bot |
| `-1003773708968` | Company HR | Not yet routed | Main Hermes bot |
| `-5205962952` | Company Management | `compliance-manager` (Kata) | Main Hermes bot |
| `1101916530` | CH Lim (DM) | `default` fallback | Main Hermes bot |

## Discovery Method

When a group's chat ID is unknown:
1. Search gateway logs: `grep -oP 'chat=-?\d+' ~/.hermes/logs/gateway.log | sort -u`
2. Groups are negative; DMs are positive
3. Identify by reading oldest messages: `grep 'chat=-NNN' ~/.hermes/logs/gateway.log | grep 'msg=' | head -1`
4. `getUpdates` via Telegram API only works if the bot is already in the group

## Compliance-Manager (Kata) Channel Prompt

Routed via `channel_prompts` in the **default** gateway's `config.yaml` (not a separate profile gateway):

```yaml
telegram:
  channel_prompts:
    '-5205962952': |
      You are Kata (型) — your company's ISO 27001 ISMS compliance specialist.
      PERSONALITY: Structured, clause-referenced, audit-focused. Precision over prose. Every document must be auditable.
      RESPONSIBILITIES: ISMS documentation (policies, procedures, SoA, risk treatment), Annex A control mapping, gap analysis, audit evidence prep, document review tracking.
      KEY PATHS: ~/brain/isms/ (policies/, procedures/, records/, soa.md, risk-treatment-plan.md).
      ALWAYS LOAD: brain-documentation, obsidian.
      BOUNDARIES: Not a legal advisor. Don't invent controls — trace to Annex A. Draft only; management approves. Never delete ISMS docs — archive instead.
      COMMUNICATION: Clause → requirement → evidence chain. Tables for control matrices. ISO 27000 definitions for "must"/"should"/"may".
```

Added 2026-06-08. Group access is via `TELEGRAM_GROUP_ALLOWED_CHATS` in `~/.hermes/.env`.

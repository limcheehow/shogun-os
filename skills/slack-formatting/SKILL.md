---
name: slack-formatting
description: "Format output for Slack-optimized delivery — mrkdwn text AND Block Kit JSON blocks (header, table, alert, section, context, actions, card, data_table). Use mrkdwn for cron job text delivery via send_message. Use Block Kit JSON for rich messages via Slack API (curl chat.postMessage)."
version: 2.0.0
author: CH Lim
license: MIT
---

# Slack Formatting — Mrkdwn & Block Kit

Slack has two delivery modes for rich content:

| Mode | How | Best for |
|------|-----|----------|
| **Mrkdwn text** | `send_message` / cron delivery | Simple messages, digests, quick notes |
| **Block Kit JSON** | curl to `chat.postMessage` with `blocks` array | Rich layouts: tables, cards, alerts, buttons |

Use the right mode based on the content. For route comparisons, corridor checks, or any structured data — **use Block Kit JSON**.

---

## Part 1: Mrkdwn Text (for send_message / cron delivery)

### Supported Syntax

| Style | Syntax | Example |
|-------|--------|---------|
| **Bold** | `*text*` | *bold text* |
| *Italic* | `_text_` | *italic text* |
| ~~Strikethrough~~ | `~text~` | ~strikethrough~ |
| `Code` | `` `text` `` | `inline code` |
| Code block | ` ``` ` `` `code` `` ` ``` ` | Multi-line monospace |
| Blockquote | `> text` | > quoted line |
| Bullet list | `• text` or `- text` | Indented lists |
| Numbered list | `1. text` | Auto-numbered |
| Link | `<https://url\|label>` | <https://example.com\|Click here> |
| Emoji | `:emoji:` | :rocket: :memo: :warning: |

### Headers
No `#` syntax in mrkdwn. Use `*bold*` as pseudo-headers or — better — use Block Kit `header` blocks for real headings.

### What to Avoid
- No `[text](url)` markdown links — use `<url|text>` instead
- No HTML tags — Slack strips them
- No pipe tables — they render as raw text
- No walls of text — break into sections

---

## Part 2: Block Kit JSON (for Slack API delivery)

Send via curl to `chat.postMessage` with a `blocks` array. Example:

```bash
curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C0B2NTXJD9U",
    "text": "Fallback text for notifications",  # shown in push notifications
    "blocks": [ ... ]
  }'
```

Available block types for messages (up to 50 blocks per message):

| Block | Purpose |
|-------|---------|
| `header` | Large bold heading (150 chars max, plain text only) |
| `section` | Text body + optional fields (key-value pairs) + optional accessory |
| `divider` | Horizontal rule |
| `table` | Structured data grid (100 rows × 20 cols) |
| `alert` | Info/success/warning/error banner |
| `context` | Small metadata text with optional inline images |
| `actions` | Row of interactive buttons |
| `image` | Inline image |
| `markdown` | Formatted markdown block (pipe tables work here!) |
| `card` | Structured card with icon, title, subtitle, body, actions |
| `carousel` | Horizontal scrollable cards (up to 10) |
| `data_table` | Rich table with pagination, sorting, filtering |
| `video` | Embedded video player |

---

### Header Block

```json
{
  "type": "header",
  "text": {
    "type": "plain_text",
    "text": "🚄 Tokyo Corridor Check — Jun 15",
    "emoji": true
  }
}
```

### Section Block (with text + fields + accessory)

```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*From:* Tokyo Marriott\n*To:* Tsutsumidori Park\n*Total:* ~50 min / ¥620"
  },
  "fields": [
    { "type": "mrkdwn", "text": "*Duration:*\n50 min" },
    { "type": "mrkdwn", "text": "*Fare:*\n¥620" },
    { "type": "mrkdwn", "text": "*Transfers:*\n3" },
    { "type": "mrkdwn", "text": "*Stroller:*\n⚠️ 1 long walk" }
  ]
}
```

### Table Block

```json
{
  "type": "table",
  "rows": [
    [
      { "type": "raw_text", "text": "Step" },
      { "type": "raw_text", "text": "Route" },
      { "type": "raw_text", "text": "Time" },
      { "type": "raw_text", "text": "Fare" }
    ],
    [
      { "type": "raw_text", "text": "1" },
      { "type": "raw_text", "text": "JR Yamanote: Ueno → Akihabara" },
      { "type": "raw_text", "text": "10 min" },
      { "type": "raw_text", "text": "¥180" }
    ],
    [
      { "type": "raw_text", "text": "2" },
      { "type": "raw_text", "text": "Tokyo Metro Ginza: Akihabara → Asakusa" },
      { "type": "raw_text", "text": "5 min" },
      { "type": "raw_text", "text": "¥260" }
    ]
  ],
  "column_settings": [
    { "align": "center" },
    {},
    { "align": "right" },
    { "align": "right" }
  ]
}
```

⚠️ **Cell limitations**: plain text only (no bold, italic, links inside cells). For formatted cells, use `rich_text` cell type.

### Alert Block

```json
{
  "type": "alert",
  "style": "error",
  "text": {
    "type": "mrkdwn",
    "text": "*Error:* \"Walk 3 min from JR Ueno to Tobu Asakusa Station\" — these stations are 1.5–2km apart in different neighborhoods."
  }
}
```

Styles: `default`, `info`, `success`, `warning`, `error`

### Context Block

```json
{
  "type": "context",
  "elements": [
    { "type": "mrkdwn", "text": ":mag: Updated by corridor check · Jun 15, 2026" }
  ]
}
```

### Actions Block (buttons)

```json
{
  "type": "actions",
  "elements": [
    {
      "type": "button",
      "text": { "type": "plain_text", "text": "↗ Open in Google Maps", "emoji": true },
      "url": "https://maps.google.com/?q=35.7100,139.7965",
      "action_id": "open_maps"
    },
    {
      "type": "button",
      "text": { "type": "plain_text", "text": "📄 View Full Itinerary", "emoji": true },
      "url": "https://docs.google.com/document/d/1SPQ-4aRVk9yCn8OVlKQMG-rLzezNfRqN2Zev5sV-Kug",
      "action_id": "view_doc"
    }
  ]
}
```

### Markdown Block (pipe tables work here!)

```json
{
  "type": "markdown",
  "text": "| Step | Route | Time | Fare |\n|------|-------|------|------|\n| 1 | JR Yamanote | 10 min | ¥180 |\n| 2 | Ginza Line | 5 min | ¥260 |\n| 3 | Walk | 10 min | — |"
}
```

The `markdown` block is special — it **does** render pipe-table syntax as actual tables. Use this as a lighter alternative to the `table` block when you don't need column settings or rich_text cells.

### Card Block

```json
{
  "type": "card",
  "icon": { "type": "emoji", "name": "train2" },
  "title": "Alternative: Via Minami-Senju",
  "subtitle": "Cheaper, faster, simpler",
  "body": [
    { "type": "mrkdwn", "text": "*JR Keihin-Tohoku* → Minami-Senju (22 min, ¥330)\n*Walk* → Tobu Minami-Senju (5 min)\n*Tobu Skytree* → Higashi-Mukojima (2 min, ¥130)\n*Walk* → Tsutsumidori Park (10 min)" }
  ],
  "actions": [
    {
      "type": "button",
      "text": { "type": "plain_text", "text": "View Route", "emoji": true },
      "url": "https://maps.google.com"
    }
  ]
}
```

---

## Part 3: Template Patterns

### Route / Corridor Check (the trip channel gold standard)

Use this structure when delivering corridor checks or route comparisons:

```
┌─ header ─────────────────────────────────────────┐
│ 🚄 Tokyo Corridor Check — Jun 15                  │
└───────────────────────────────────────────────────┘
┌─ alert (error) ───────────────────────────────────┐
│ ❌ Error: "Walk 3 min from JR Ueno to..."         │
│ These stations are 1.5-2km apart                  │
└───────────────────────────────────────────────────┘
┌─ section ─────────────────────────────────────────┐
│ Correct route: Add the Ginza Line step            │
└───────────────────────────────────────────────────┘
┌─ table ───────────────────────────────────────────┐
│ Step │ Route                     │ Time  │ Fare   │
│ 1    │ Marriott → Shinagawa      │ 10 min │ —     │
│ 2    │ JR Yamanote → Ueno        │ 13 min │ ¥180  │
│ 3    │ Ginza Line → Asakusa      │ 5 min  │ ¥260  │
│ ...                                              │
│      │ TOTAL                     │ ~50 min│ ¥620  │
└───────────────────────────────────────────────────┘
┌─ card ────────────────────────────────────────────┐
│ ✅ Better alternative: Via Minami-Senju           │
│ Cheaper, faster, simpler                          │
│ • 1 fewer transfer                                │
│ • ¥160 cheaper                                    │
│ • Better with toddler/stroller                    │
│ [View Route]                                      │
└───────────────────────────────────────────────────┘
┌─ section ─────────────────────────────────────────┘
│ ✅ Correct items:                                  │
│ • Walk 700m → park — accurate ✓                    │
│ • Train timing ~10 min — reasonable ✓              │
│ • Alternative route ~30 min — accurate ✓           │
└───────────────────────────────────────────────────┘
┌─ context ──────────────────────────────────────────┐
│ 🔍 Source: Japan trip doc · Jun 15, 2026           │
└────────────────────────────────────────────────────┘
```

### Alert / Status Reports

```
header:   📊 Morning Briefing — Mon
section:  Key stats
table:    Stock | Price | Change | RSI
alert:    ⚠️ Weather alert for Tokyo
context:  Generated at 8:00 AM
```

### Digest / News

```
header:   📰 Daily News Digest
section:  Top stories with links
divider:  ---
section:  More headlines
actions:  [View All] [Manage Preferences]
context:  Powered by Hermes
```

---

## Part 4: How to Choose

| Content Type | Use |
|-------------|-----|
| Simple text, short alerts | `send_message` with mrkdwn |
| Route/trip corridor checks | Block Kit JSON via curl (header + table + alert + card) |
| Structured data (stocks, scores) | Block Kit table block |
| Error/warning/success messages | Block Kit alert block |
| Multi-option comparisons | Block Kit card + carousel |
| Long digests with sections | Block Kit header + section + divider |
| Interactive follow-ups | Block Kit actions (buttons) |
| Push notification text | Always set `text` field in JSON payload |

### Quick reference for curl delivery

```bash
# Send a Block Kit message to Slack channel
curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C0B2NTXJD9U",
    "text": "Corridor check results",
    "blocks": [
      { "type": "header", "text": { "type": "plain_text", "text": "🚄 Corridor Check", "emoji": true } },
      { "type": "divider" },
      { "type": "section", "text": { "type": "mrkdwn", "text": "Results here..." } }
    ]
  }'
```

---

## Part 5: What to Avoid

- Do NOT use `#` or `##` in mrkdwn text — use Block Kit `header` block instead
- Do NOT use `[text](url)` markdown links — use `<url|text>` in mrkdwn or `button.url` in Block Kit
- Do NOT use HTML tags — Slack strips them
- Do NOT send raw pipe tables in mrkdwn — they render as literal text
- Do NOT exceed 50 blocks per message
- Do NOT put mrkdwn formatting inside `table` block cells — use `rich_text` cell type instead
- Do NOT use `table` for data that needs clickable links inside cells — use `section` with fields instead
- Always include `text` field in Block Kit JSON payloads — it's shown in push notifications
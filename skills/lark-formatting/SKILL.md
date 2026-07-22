---
name: lark-formatting
version: 1.0.0
description: |
  Format messages for Lark (Feishu) delivery — text formatting,
  CardKit JSON cards, markdown, and interactive components.
triggers:
  - "lark message format"
  - "format for lark"
  - "lark card"
---

# Lark Formatting

> **Format output for Lark-optimized delivery.** Lark supports three message types:
> **text** (plain text), **interactive** (CardKit JSON), and **post** (rich text).

## Message Types

### 1. Plain Text (msg_type: text)

Simple text with limited formatting. Supports markdown-like syntax:

```json
{
  "msg_type": "text",
  "content": "{\"text\": \"Message with **bold**, *italic*, `code`, and [link](url)\"}"
}
```

| Format | Syntax | Example |
|--------|--------|---------|
| Bold | `**text**` | **bold** |
| Italic | `*text*` | *italic* |
| Code | `` `text` `` | `code` |
| Link | `[text](url)` | [Lark](https://lark.com) |
| Line break | `\n` | New line |

**Limitations:** Text messages are single JSON — max ~30KB. No tables, buttons, or images.

### 2. CardKit (msg_type: interactive) — RECOMMENDED

Rich interactive cards with header, body, buttons, tables, and images.

**Basic card structure:**
```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "Card Title"},
    "template": "blue"
  },
  "elements": [
    {"tag": "markdown", "content": "**Key info:** This is the body."},
    {"tag": "hr"},
    {"tag": "column_set", "flex_mode": "bisect", "background_style": "default",
     "columns": [
       {"tag": "column", "width": "weighted", "weight": 1,
        "elements": [{"tag": "markdown", "content": "**Left column**\nContent here"}]},
       {"tag": "column", "width": "weighted", "weight": 1,
        "elements": [{"tag": "markdown", "content": "**Right column**\nContent here"}]}
     ]},
    {"tag": "note", "elements": [{"tag": "plain_text", "content": "Footer text"}]}
  ]
}
```

**Available header templates:**
- `blue` — Default info
- `green` — Success
- `red` — Error/alert
- `orange` — Warning
- `purple` — Highlight
- `grey` — Neutral

**Available element tags:**

| Tag | Purpose |
|-----|---------|
| `markdown` | Formatted text body |
| `div` | Wrapper for inline elements |
| `hr` | Horizontal divider |
| `column_set` | Multi-column layout |
| `button` | Action button with URL or callback |
| `image` | Embedded image |
| `note` | Small footer text |
| `plain_text` | Unformatted text (for headers, buttons, notes) |

### 3. Post / Rich Text (msg_type: post)

Legacy rich text format (superseded by CardKit in most cases).

```json
{
  "msg_type": "post",
  "content": "{\"zh_cn\":{\"title\":\"Title\",\"content\":[[{\"tag\":\"text\",\"text\":\"Hello \"},{\"tag\":\"a\",\"text\":\"Lark\",\"href\":\"https://lark.com\"}]]}}"
}
```

## CardKit Templates for Shogun OS

### Scrum Report Card

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "\[[[[SCRUM\] — {{DATE}}"}},
    "template": "blue"
  },
  "elements": [
    {"tag": "markdown", "content": "**Team:** {{TEAM_NAME}} ({{MEMBER_COUNT}} members)"},
    {"tag": "hr"},
    {"tag": "markdown", "content": "{{SCRUM_SUMMARY}}"},
    {"tag": "hr"},
    {"tag": "column_set", "flex_mode": "bisect", "background_style": "default",
     "columns": [
       {"tag": "column", "width": "weighted", "weight": 1,
        "elements": [{"tag": "markdown", "content": "**✅ Completed**\n{{COMPLETED_ITEMS}}"}]},
       {"tag": "column", "width": "weighted", "weight": 1,
        "elements": [{"tag": "markdown", "content": "**🚧 Blockers**\n{{BLOCKERS}}"}]}
     ]},
    {"tag": "note", "elements": [{"tag": "plain_text", "content": "Updated: {{TIMESTAMP}}"}]}
  ]
}
```

### Alert / Warning Card

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "⚠️ Alert"},
    "template": "red"
  },
  "elements": [
    {"tag": "markdown", "content": "**Issue:** {{ISSUE_DESC}}\n\n**Action required:** {{ACTION}}"},
    {"tag": "hr"},
    {"tag": "button", "text": {"tag": "plain_text", "content": "View Details"},
     "type": "primary", "url": "{{URL}}"}
  ]
}
```

## Mentions

To mention a user in a Lark message, use the `@_user_1` format in markdown:

```json
{"tag": "markdown", "content": "Hello <at user_id=\"ou_xxx\">@Alice</at>, please review this."}
```

Or in text content:
```
text: "Hello @_user_1, please review this."
```

(Integer user IDs are mapped to user order in the chat: `@_user_1`, `@_user_2`, etc.)

## Best Practices

1. **Use CardKit (interactive) for any structured output** — tables, comparisons, reports
2. **Use plain text only for simple DMs** — faster, less tokens
3. **Add a `note` element as a footer** — shows smaller, grey text
4. **Use `wide_screen_mode: true`** — prevents card from being too narrow on mobile
5. **Buttons need a `url` or `multi_url`** — they don't execute actions natively
6. **CardKit elements max 50 per card** — split large reports into multiple cards
7. **Text messages max ~30KB** — use CardKit for larger content

## Comparison with Slack Format

| Feature | Slack (Block Kit) | Lark (CardKit) |
|---------|-------------------|----------------|
| Markdown in body | ✅ text blocks | ✅ markdown elements |
| Buttons | ✅ button elements | ✅ button elements |
| Image | ✅ image block | ✅ image element |
| Multi-column | ✅ section with fields | ✅ column_set |
| Divider | ✅ divider block | ✅ hr element |
| Color header | ❌ (no header) | ✅ header with template color |
| Footer | ✅ context block | ✅ note element |
| Input forms | ✅ input blocks | ❌ (not supported) |
| Message size limit | ~40KB | ~30KB |
| Setup complexity | JSON blocks | JSON elements |
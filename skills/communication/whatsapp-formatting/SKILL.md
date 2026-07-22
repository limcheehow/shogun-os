---
name: whatsapp-formatting
description: "Convert markdown-formatted text into WhatsApp-optimized plain text. WhatsApp supports only bold, italic, strikethrough, monospace, ordered/unordered lists, and blockquotes — NO tables, headings, or hyperlinks."
version: 1.0.0
author: user
license: MIT
---

# WhatsApp Text Formatting

WhatsApp has **minimal** formatting support. This skill defines how to convert rich markdown content (tables, headings, links, etc.) into WhatsApp-friendly plain text.

## Supported WhatsApp Formatting

| Style | Markdown Syntax | WhatsApp Syntax |
|-------|-----------------|-----------------|
| Bold | `**text**` | `*text*` |
| Italic | `*text*` | `_text_` |
| Strikethrough | `~~text~~` | `~text~` |
| Monospace / Code | `` `text` `` | `` `text` `` |
| Unordered list | `- item` or `* item` | `- item` or `* item` |
| Ordered list | `1. item` | `1. item` |
| Blockquote | `> quote` | `> quote` |

## What Does NOT Work

- **# Headers / ## Headers** — silently stripped or shows as raw `#` text
- **Tables / pipe tables** — rendered as raw `|` characters, looks broken
- **`[text](url)` links** — shows as raw markdown; only bare URLs work
- **`---` horizontal rules** — shows as raw dashes
- **Nested formatting** — erratic support, avoid

## Conversion Rules

### Headings → Bold text
```
## Section Title → *Section Title*
# Main Title    → *MAIN TITLE* (uppercase for emphasis)
```

### Tables → Indented bullet lists
Use `➤` or `→` as separators instead of `|`. Break each row into a compact line.

```
| Day | Date | Activity |
|-----|------|----------|
| 1   | Mon  | Arrive   |

→

*Day 1 (Mon)* — Arrive
*Day 2 (Tue)* — Sightseeing
*Day 3 (Wed)* — Museum
```

### Links → Bare URL with context
```
[Click here](https://example.com) → https://example.com
```

Omit the link text if it's obvious from context. If the URL is long, mention it in words.

### Code blocks → Wrap in backticks
Short inline code: keep as `` `code` ``.
Multi-line code blocks: prefix each line with `` ` `` or use a single backtick fence. For longer blocks, use blockquote `>` format.

### Horizontal rules → Section break via emoji
Use emoji section markers instead (`📍`, `📋`, `ℹ️`, `⚠️`, `📌`).

### Multiple paragraphs → line breaks
WhatsApp respects single `\n` within a message. Use double `\n` between sections.

## Structure Guidelines

**Keep lines short** — WhatsApp wraps poorly on lines over 50 characters.

**Use emoji as visual headers** since `#` doesn't work:
```
*JAPAN TRIP — Jun 20-27*

📍 *Itinerary*
  ➤ Day 1 (Sat) — Arrive
  ➤ Day 2 (Sun) — Explore

🏨 *Hotels*
  ➤ Jun 20-24 — Tokyo Marriott

⚠️ *Notes*
  Return flight changed to 20:55
```

**Key emoji separators:**
- 📍 — Itinerary / Timeline / Steps
- 🏨 — Accommodation
- ✈️ — Travel / Transport / Flights
- ⚠️ — Warnings / Changes
- ℹ️ — Info / Notes
- 📋 — Lists / Summary
- 🎯 — Action items
- ✅ — Completed / Confirmed
- 📌 — Important / Pinned
- 💡 — Tip
- ❌ — Problem / Issue

**Indent sub-items** with 2 spaces (not tabs — WhatsApp expands tabs oddly).
**Bold section headers** with `*header*` — this is the closest equivalent to `##`.

## Example: Status Update

**Bad:**
```
## Status Report
- **Project A**: ✅ On track
- **Project B**: ⚠️ Delayed
```

**Good:**
```
*STATUS REPORT*

📋 *Project A* ✅ On track
📋 *Project B* ⚠️ Delayed — ETA revised to Friday
```

## When to Use

This conversion should be applied whenever delivering content to a **WhatsApp** platform — whether via the built-in WhatsApp gateway, a profile-specific bridge, or any automated WhatsApp delivery.

Load this skill with `skill_view(name='whatsapp-formatting')` in any WhatsApp-targeted skill or gateway personality prompt.
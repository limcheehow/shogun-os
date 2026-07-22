# Company Gmail → Gbrain Email Pipeline

Full pipeline for ingesting team emails into gbrain knowledge base.

## Architecture

```
Gmail API ──► collect-gmail-team.py ──► ~/brain/data/email/*.md ──► gbrain import ──► brain pages
  │                │                          │                          │
  │ ① fetch        │ ② PII scrub            │ ③ markdown files         │ ④ parse→chunk→DB
  │   metadata     │    format as .md        │    9.5MB / 2,371 files   │    → data/email/<slug>
  ▼                ▼                          ▼                          ▼
9 inboxes      SA-DWD auth              YAML frontmatter            3,480 pages
@example.com  --subject per user       type: email                 under data/email/
```

## Step 1: Gmail Collection

**Script:** `~/.hermes/scripts/collect-gmail-team.py` (wraps via `collect-gmail-cron.sh`)

Uses Google SA-DWD (`--subject` flag) to impersonate team inboxes:
```
cheehow@, hana@, kunna@, anwar@, liyana@, syazwan@, fitri@, ashraf@, iskandar@
```

- 50 emails per user, last 7 days
- Metadata only (Subject, From, Date, snippet) — NOT full bodies
- PII scrubbing: emails → `[EMAIL]`, phones → `[PHONE]`, capped at 2000 chars

## Step 2: Markdown File Format

Each email becomes `~/brain/data/email/email-{timestamp}-{slug}.md`:

```yaml
---
title: "Subject line"
type: email
date: Sat, 23 May 2026 02:03:29 +0000
from: Company <support@example.com>
gmail_id: 19e5292c0caa2fd0
tags: [email, gmail]
---

# Subject line
**From:** ...
**Date:** ...
**Labels:** INBOX, CATEGORY_FORUMS

[PII-scrubbed snippet]
```

## Step 3: Gbrain Import

`gbrain import ~/brain/data/email --no-embed --workers 8` processes each `.md`:

| Stage | What happens |
|-------|-------------|
| Parse | YAML frontmatter → `type`, `date`, `from`, `tags` |
| Slug | `slugifyPath()` strips `.md`, preserves path → `data/email/email-...` |
| Chunk | Body split via recursive markdown chunker |
| Dedup | Content hash vs existing pages → "unchanged" if identical |
| Write | `put_page` → Postgres → chunks → FTS5 index |
| Embed | Skipped with `--no-embed` (backfilled via `gbrain embed --stale`) |

## Memory Issue

Default `--workers 8` on 20-CPU/15GB-RAM system → 14GB RSS for 2,279 files.
Fix: use batched subagent approach (`gbrain-batched-import` skill) with `--workers 1`.
The markdown files themselves are only 9.5MB total — memory is all in connection pools and JIT heap.

## Key Files

| File | Purpose |
|------|---------|
| `~/.hermes/scripts/collect-gmail-team.py` | Multi-user Gmail collector (SA-DWD) |
| `~/.hermes/scripts/collect-gmail-cron.sh` | Cron wrapper |
| `~/.hermes/scripts/collect-gmail.py` | Single-user Gmail collector (OAuth) |
| `~/brain/data/email/` | Output directory (2,371 .md files) |
| `~/gbrain/src/commands/import.ts` | Import command handler |
| `~/gbrain/src/core/import-file.ts` | Per-file processing (parse→chunk→write) |
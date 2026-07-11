---
name: gbrain-frontmatter-guard
description: "Validate YAML frontmatter on every brain write — gate malformed YAML, missing required fields, incorrect types, and null bytes before they corrupt pages."
version: 1.0.0
author: Your Company
tags: [gbrain, frontmatter, validation, quality]
---
# gbrain Frontmatter Guard

**Always run before any `mcp_gbrain_put_page` call.** Corrupted frontmatter breaks search, rendering, and embedding.

## Validation Checklist (run before every write)

### 1. YAML Parsability
```yaml
# MUST parse with Python yaml.safe_load
# NO: tabs, mixed indentation, unquoted colons, trailing spaces in values
```

### 2. Required Fields

| Page type | Required | Optional |
|-----------|----------|----------|
| `person` | `title`, `type: person`, `tags` | `email`, `role`, `team` |
| `company` | `title`, `type: company`, `tags` | `url`, `industry` |
| `project` | `title`, `type: project`, `tags` | `status`, `team` |
| `idea` | `title`, `type: idea`, `date`, `tags` | — |
| `reference` | `title`, `type: reference`, `source`, `tags` | `ingested` |
| `decision` | `title`, `type: decision`, `date`, `tags` | `context` |
| `conversation` | `title`, `type: conversation`, `date`, `tags` | `participants` |
| `weekly`/`daily` | `title`, `type`, `date`, `tags` | — |

### 3. Rules

| Rule | Check | Fix |
|------|-------|-----|
| No null bytes | Content has no `\x00` | Strip them |
| No tabs in YAML | Only spaces for indentation | Convert to spaces |
| Title not empty | `title:` has a value | Add descriptive title |
| Type is valid | One of: person, company, project, idea, reference, decision, conversation, weekly, daily, concept, note | Fix or add |
| Tags are list | `tags: [a, b]` not `tags: a` | Wrap in brackets |
| Date format | `YYYY-MM-DD` ISO format | Fix date |
| No duplicate keys | YAML has no repeated keys | Deduplicate |
| Trailing whitespace | No spaces at end of lines | Trim |

### 4. Slug Hygiene
- Slugs: `lowercase-hyphenated`, no spaces, no special chars
- Path prefixes: `people/`, `companies/`, `projects/`, `ideas/`, `concepts/`, `references/`, `conversations/`, `decisions/`, `daily/`, `weekly/`

## Pre-Write Hook

Before calling `mcp_gbrain_put_page`:

1. Validate the full content string
2. Parse frontmatter with `yaml.safe_load`
3. Check all rules above
4. If any rule fails → FIX before writing, never write broken content

## Batch Null-Byte Scanner

When importing external markdown repos into the brain or syncing git-tracked markdown, null bytes (`\x00`) in files can corrupt git diffs, break YAML frontmatter parsing, and silently truncate content during sync.

Use the bundled script to scan and fix:

```bash
# Scan entire brain repo for null bytes (git-tracked files only)
python3 ~/.hermes/skills/gbrain/gbrain-frontmatter-guard/scripts/scan_null_bytes.py --path ~/brain --git-only

# Scan + fix in one pass (recommended: git commit first)
python3 ~/.hermes/skills/gbrain/gbrain-frontmatter-guard/scripts/scan_null_bytes.py --path ~/brain --git-only --fix

# Scan a specific directory (all files, not git-filtered)
python3 ~/.hermes/skills/gbrain/gbrain-frontmatter-guard/scripts/scan_null_bytes.py --path ~/brain/projects

# JSON output for programmatic consumption
python3 ~/.hermes/skills/gbrain/gbrain-frontmatter-guard/scripts/scan_null_bytes.py --path ~/brain --git-only --json
```

The script exits 0 on clean, 1 on findings (without `--fix`), making it safe to use in CI/pre-commit hooks or as a cron health check.

## Pitfalls

- ❌ Writing without checking frontmatter first
- ❌ Tabs in YAML (causes parse failures that silently lose content)
- ❌ Missing `type` field (page becomes unsearchable by type)
- ❌ Non-ISO dates (timeline entries break silently)
- ❌ Allowing null bytes from file reads/OCR to propagate to brain pages
- ❌ Syncing git repos with null-byte-laden files — diffs look corrupted and `git pull --rebase` can silently truncate content
- ❌ Pushing null-byte files to shared project repos — other editors see binary-diff warnings for text files
---
name: gbrain-capture
description: "Quick capture of thoughts, ideas, and observations to gbrain — preserve exact phrasing, file under ideas/ or concepts/."
version: 1.0.0
author: Your Company
tags: [gbrain, capture, ideas, thoughts]
---
# gbrain Capture

Capture original thinking, ideas, and observations to the brain. Preserves the user's exact phrasing — never paraphrase original thought.

## When to Capture

- User shares a novel idea, thesis, or framework
- User makes an insightful observation about a person/company/project
- User expresses a decision, commitment, or belief
- You generate a substantive insight during your work
- End of a conversation that produced useful content

**Do NOT capture:** operational messages (ok, thanks, greetings), single-word replies, routine status updates.

## Capture Format

```yaml
---
title: "Idea: [concise title]"
type: idea  # idea | concept | decision | hunch
tags: [idea]
date: "2026-06-10"
---
**Capture:** The user's exact words go here — verbatim, no paraphrasing.

**Context:** Brief context of what prompted this (optional).

**Cross-links:** [[people/someone]] [[companies/some-company]]
```

## Hard Rules

1. **EXACT phrasing** — the user's language IS the insight. Do NOT rephrase, summarize, or "improve" the original wording.
2. **File under `ideas/` or `concepts/`** — not `projects/` or `people/`
3. **Cross-link** — use `mcp_gbrain_add_link` from every mentioned entity TO this page
4. **Tag** — add `idea` tag via `mcp_gbrain_add_tag`
5. **One page per distinct idea** — don't batch unrelated ideas

## Quick Workflow

```
mcp_gbrain_search(idea_title)          # check for duplicates
mcp_gbrain_put_page(slug, content)     # create the page
mcp_gbrain_add_tag(slug, "idea")       # tag it
mcp_gbrain_add_link(from=entity, to=slug, context="mentioned this idea")
```

## Pitfalls

- ❌ Paraphrasing the user's original thinking — this destroys the signal
- ❌ Batching unrelated ideas into one page (low recall)
- ❌ Skipping back-links (unlinked ideas are invisible)
- ❌ Over-capturing operational chit-chat
---
name: coding-workflow
description: Master workflow for all coding tasks at your company — delegates to coding-agent profile. Triggers include "build", "implement", "code", "fix bug", "add feature", "refactor", "deploy", "release".
category: software-development
---

# Coding Workflow — Delegate to coding-agent

All coding work is handled by the dedicated `coding-agent` profile. This skill documents the routing convention.

## When to Trigger

Any of these triggers:
- "build X", "implement X", "code X"
- "fix bug", "debug", "why is X failing"
- "add feature", "new endpoint", "create component"
- "refactor", "clean up", "improve"
- "deploy", "release", "ship"
- "PR review", "code review", "check my changes"
- "write tests", "run test suite"
- "autoship", "ship this", "execute the plan"

## Routing

```
User request → Load this skill → Delegate to coding-agent
```

The coding-agent follows the your company Superpowers 11-step workflow:

```
Brainstorm → Plan → Commit Docs → TDD → Cleanup → Simplify → Self-Review → PR → Deploy → Release → Verify
```

Fast path: `/autoship` runs TDD→Simplify→Review→PR automatically from a written plan.

## How to Delegate

**Option A — CLI switch (recommended for interactive work):**
```
Tell user: "Let me hand this to the coding agent."
Then: instruct user to run `coding-agent chat` and describe the task there.
```

**Option B — Direct delegation (for background tasks):**
Use `delegate_task` with context describing the full task, project path, and relevant skills. The coding-agent profile runs with its own skills, SOUL.md, and toolset.

**Option C — Via cron (for automated CI/CD tasks):**
Create cron jobs under the coding-agent profile using `hermes --profile coding-agent cron create ...`

## What NOT to Route

- Product management (PRDs, epics, sprint planning) → product-manager profile
- HR, onboarding, KPIs → Kizuna profile
- Marketing, content, social → Haiku profile
- Dashboard content editing → product-manager profile
- Hermes configuration/management → this (default) profile

## Slack Coding-Agent Channel

To set up a dedicated Slack channel that auto-loads the coding agent persona — no per-message prompting needed — see `references/slack-coding-agent-channel.md`. The recipe covers: channel prompt, platform toolset expansion, external skill dirs, YAML-safe config editing, and gateway restart.

## Key Paths

- Coding agent profile: `~/.hermes/profiles/coding-agent/`
- CLI alias: `coding-agent chat`
- Skills: `~/.hermes/profiles/coding-agent/skills/`
- Superpowers repo: https://github.com/your-company/your-company-superpowers
- Upgrade procedure: `references/upgrading-from-superpowers.md`
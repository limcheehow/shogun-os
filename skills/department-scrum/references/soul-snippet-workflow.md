# SOUL.md Workflow Enforcement Snippet

Add this section to every department profile's SOUL.md. It enforces the
disciplined workflow gate sequence for any feature, bug, or change request.

## Snippet

```markdown
## Workflow Enforcement (MANDATORY)

When any user request involves building, fixing, or changing functionality —
whether code, scripts, cron jobs, skills, or configuration — you MUST follow
this gate sequence BEFORE any implementation:

1. **Triage** — Classify the request (feature, bug, refactor, config change)
2. **RCA / Research** — Understand the root cause or requirements before writing code
3. **Brainstorm** — Explore approaches, map scope, get confirmation before executing
4. **Plan** — Write an implementation plan (bite-sized tasks, file paths, code outlines)
5. **TDD** — Write tests first, then implement
6. **E2E** — End-to-end validation against real systems, not mocks

**Skipping the workflow is a critical defect, not a shortcut.** If you catch
yourself jumping to implementation without completing Phase 1 (RCA/Research),
STOP and return to the workflow.

Signal phrases that trigger this workflow: feature, bug, fix, add, implement,
build, refactor, new endpoint, "why is X failing", change behavior.

When in doubt, load the workflow skill before proceeding.
```

## Integration

In `generate-profile.py`, this snippet is injected into every generated
SOUL.md after the "Always Load Before Working" section and before the
"Boundaries" section.

The `company-workflow` skill (in `skills/company-workflow/`) provides the
full gate sequence details. Each profile loads it as a shared skill.

---
name: company-workflow
description: "Mandatory workflow enforcement for all feature/bug requests in Company OS. Gate sequence: triage → RCA → brainstorm → plan → TDD → E2E. No skipping."
version: 1.0.0
tags: [shared, workflow, enforcement, quality, gates]
triggers:
  - "feature"
  - "bug"
  - "fix"
  - "add"
  - "implement"
  - "build"
  - "refactor"
  - "new endpoint"
  - "why is X failing"
  - "change behavior"
---

# Company Workflow — Mandatory Gate Sequence

When any user request involves building, fixing, or changing functionality —
whether code, scripts, cron jobs, skills, or configuration — you MUST follow
this gate sequence BEFORE any implementation.

## The 6 Gates

### Gate 1: Triage
Classify the request:
- **Feature** — new functionality
- **Bug** — broken behavior that worked before
- **Refactor** — restructure without behavior change
- **Config** — settings/infrastructure change

Determine impact: How many files? How many users affected? Is there a deadline?

### Gate 2: RCA / Research
Understand the root cause or requirements BEFORE writing code:
- For bugs: reproduce the symptom, trace the causal chain, find the exact line
- For features: research existing patterns, check for similar implementations
- For refactors: map the current structure, identify all callers/dependencies

**Do not skip to implementation.** If you can't explain WHY the bug happens
or WHAT the feature should do in 2-3 sentences, you haven't done RCA.

### Gate 3: Brainstorm
Explore approaches before committing to one:
- List 2-3 possible approaches with trade-offs
- Consider: simplicity, maintainability, performance, security
- Map scope: how many files, how many tests need updating
- Get confirmation from the user before proceeding

### Gate 4: Plan
Write an implementation plan:
- Bite-sized tasks (1 task = 1 commit)
- File paths for each change
- Code outlines (function signatures, data structures)
- Test cases to write
- Rollback plan

### Gate 5: TDD (Test-Driven Development)
Write tests FIRST, then implement:
- Write a failing test that captures the desired behavior
- Implement the minimum code to pass the test
- Refactor with the test as a safety net

### Gate 6: E2E (End-to-End Validation)
Validate against real systems, not mocks:
- Exercise the real code path
- Verify the actual output
- Check for regressions in adjacent areas
- Confirm the fix/feature works in the production-like environment

## When to Skip Gates

| Gate | Can Skip? | When |
|---|---|---|
| 1. Triage | ❌ Never | — |
| 2. RCA | Only for trivial config changes (1 line, 1 file) |
| 3. Brainstorm | Only for single-file fixes with an obvious approach |
| 4. Plan | Only for changes < 5 files with clear scope |
| 5. TDD | Only for non-code changes (config, docs) |
| 6. E2E | ❌ Never | — |

**When in doubt, don't skip.** The cost of a skipped gate is always higher
than the time saved.

## Pitfalls

### "This is simple, I'll just fix it"
The most common reason for skipping gates. "Simple" fixes that skip RCA
often mask deeper issues. The 5-minute RCA saves the 5-hour debugging session
next week.

### Solving symptoms instead of root cause
If you fix the symptom without understanding the cause, the bug will recur
in a different form. Always trace to the root cause before implementing a fix.

### Implementing before planning
Writing code before mapping scope leads to scope creep, missed edge cases,
and incomplete tests. Plan first, implement second.

### Mocks hiding integration bugs
Unit tests with mocks can pass while the real system is broken. Always
validate the real path in Gate 6.

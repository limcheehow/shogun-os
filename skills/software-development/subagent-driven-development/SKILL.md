---
name: subagent-driven-development
description: "Execute plans via delegate_task subagents (2-stage review)."
version: 2.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, subagent, implementation, workflow, parallel]
    related_skills: [writing-plans, requesting-code-review, test-driven-development]
---

# Subagent-Driven Development

## Overview

Execute implementation plans by dispatching fresh subagents per task with systematic two-stage review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## When to Use

Use this skill when:
- You have an implementation plan (from writing-plans skill or user requirements)
- Tasks are mostly independent
- Quality and spec compliance are important
- You want automated review between tasks

**vs. manual execution:**
- Fresh context per task (no confusion from accumulated state)
- Automated review process catches issues early
- Consistent quality checks across all tasks
- Subagents can ask questions before starting work

## The Process

### 1. Read and Parse Plan

Read the plan file. Extract ALL tasks with their full text and context upfront. Create a todo list:

```python
# Read the plan
read_file("docs/plans/feature-plan.md")

# Create todo list with all tasks
todo([
    {"id": "task-1", "content": "Create User model with email field", "status": "pending"},
    {"id": "task-2", "content": "Add password hashing utility", "status": "pending"},
    {"id": "task-3", "content": "Create login endpoint", "status": "pending"},
])
```

**Key:** Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context.

### 2. Per-Task Workflow

For EACH task in the plan:

#### Step 1: Dispatch Implementer Subagent

Use `delegate_task` with complete context:

```python
delegate_task(
    goal="Implement Task 1: Create User model with email and password_hash fields",
    context="""
    TASK FROM PLAN:
    - Create: src/models/user.py
    - Add User class with email (str) and password_hash (str) fields
    - Use bcrypt for password hashing
    - Include __repr__ for debugging

    FOLLOW TDD:
    1. Write failing test in tests/models/test_user.py
    2. Run: pytest tests/models/test_user.py -v (verify FAIL)
    3. Write minimal implementation
    4. Run: pytest tests/models/test_user.py -v (verify PASS)
    5. Run: pytest tests/ -q (verify no regressions)
    6. Commit: git add -A && git commit -m "feat: add User model with password hashing"

    PROJECT CONTEXT:
    - Python 3.11, Flask app in src/app.py
    - Existing models in src/models/
    - Tests use pytest, run from project root
    - bcrypt already in requirements.txt
    """,
    toolsets=['terminal', 'file']
)
```

#### Step 1.5: TDD Gate (MANDATORY — runs BEFORE spec review)

Before spec review, dispatch a TDD verification gate to confirm the implementer followed RED-GREEN-REFACTOR:

```python
delegate_task(
    goal="TDD Gate: Verify RED-GREEN-REFACTOR was followed for Task 1",
    context="""
    TDD EVIDENCE TO CHECK:
    1. Read the git log for this task: git log --oneline -10
    2. Each new feature must show test-before-code evidence:
       - "test: [description]" commits BEFORE "feat: [description]" commits (RED→GREEN)
       - "refactor: [description]" commits optional but must come after green
       - Combined commits only acceptable if message explicitly states "RED→GREEN, test written first"
    3. Run full test suite: pytest tests/ -q — confirm ALL pass with no regressions

    TDD GATE CHECKLIST:
    - [ ] Does git log show test commits BEFORE implementation commits?
    - [ ] Did tests fail before implementation? (verified by commit order)
    - [ ] Does each production code change have a corresponding test?
    - [ ] Do all tests pass now (including existing tests)?
    - [ ] Are tests testing real behavior (not just mock assertions)?

    VERDICT:
    - TDD_PASS: Clear RED→GREEN evidence, all tests pass, full coverage
    - TDD_FAIL: Missing evidence — specify exactly what's missing and why

    If TDD_FAIL: The task implementation is INVALID. Do NOT proceed to spec review.
    Re-dispatch the implementer with stricter TDD requirements and a warning.
    """,
    toolsets=['terminal', 'file']
)
```

**If TDD Gate fails:** The entire implementation is invalid. Delete the implementation code, re-dispatch the implementer with stricter TDD enforcement in the goal. Never proceed to spec review with a failing TDD gate.

**If TDD Gate passes:** Proceed to spec compliance review.

#### Step 2: Dispatch Spec Compliance Reviewer

After the implementer completes, verify against the original spec:

```python
delegate_task(
    goal="Review if implementation matches the spec from the plan",
    context="""
    ORIGINAL TASK SPEC:
    - Create src/models/user.py with User class
    - Fields: email (str), password_hash (str)
    - Use bcrypt for password hashing
    - Include __repr__

    CHECK:
    - [ ] All requirements from spec implemented?
    - [ ] File paths match spec?
    - [ ] Function signatures match spec?
    - [ ] Behavior matches expected?
    - [ ] Nothing extra added (no scope creep)?

    OUTPUT: PASS or list of specific spec gaps to fix.
    """,
    toolsets=['file']
)
```

**If spec issues found:** Fix gaps, then re-run spec review. Continue only when spec-compliant.

#### Step 3: Dispatch Code Quality Reviewer

After spec compliance passes:

```python
delegate_task(
    goal="Review code quality for Task 1 implementation",
    context="""
    FILES TO REVIEW:
    - src/models/user.py
    - tests/models/test_user.py

    CHECK:
    - [ ] Follows project conventions and style?
    - [ ] Proper error handling?
    - [ ] Clear variable/function names?
    - [ ] Adequate test coverage?
    - [ ] No obvious bugs or missed edge cases?
    - [ ] No security issues?

    OUTPUT FORMAT:
    - Critical Issues: [must fix before proceeding]
    - Important Issues: [should fix]
    - Minor Issues: [optional]
    - Verdict: APPROVED or REQUEST_CHANGES
    """,
    toolsets=['file']
)
```

**If quality issues found:** Fix issues, re-review. Continue only when approved.

#### Step 4: Mark Complete

```python
todo([{"id": "task-1", "content": "Create User model with email field", "status": "completed"}], merge=True)
```

### 3. Final Review

After ALL tasks are complete, dispatch a final integration reviewer:

```python
delegate_task(
    goal="Review the entire implementation for consistency and integration issues",
    context="""
    All tasks from the plan are complete. Review the full implementation:
    - Do all components work together?
    - Any inconsistencies between tasks?
    - All tests passing?
    - Ready for merge?
    """,
    toolsets=['terminal', 'file']
)
```

### 4. Verify and Commit

```bash
# Run full test suite
pytest tests/ -q

# Review all changes
git diff --stat

# Final commit if needed
git add -A && git commit -m "feat: complete [feature name] implementation"
```

## Task Granularity

**Each task = 2-5 minutes of focused work.**

**Too big:**
- "Implement user authentication system"

**Right size:**
- "Create User model with email and password fields"
- "Add password hashing function"
- "Create login endpoint"
- "Add JWT token generation"
- "Create registration endpoint"

## Red Flags — Never Do These

- Start implementation without a plan
- Skip TDD Gate (Step 1.5) — runs BEFORE spec review, never skip
- Proceed when TDD gate returns TDD_FAIL — re-dispatch implementer, don't patch
- Skip reviews (TDD gate OR spec compliance OR code quality)
- Run reviews out of order: TDD Gate → Spec → Quality (never violate)
- Proceed with unfixed critical/important issues
- Dispatch multiple implementation subagents for tasks that touch the same files
- Make subagent read the plan file (provide full text in context instead)
- Skip scene-setting context (subagent needs to understand where the task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues → implementer fixes → review again)
- Let implementer self-review replace actual review (all three gates are needed)
- **Start code quality review before spec compliance is PASS** (wrong order)
- **Start spec review before TDD gate is TDD_PASS** (wrong order)
- Move to next task while any review has open issues

## Handling Issues

### If Subagent Asks Questions

- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

### If Reviewer Finds Issues

- Implementer subagent (or a new one) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

### If Subagent Fails a Task

- Dispatch a new fix subagent with specific instructions about what went wrong
- Don't try to fix manually in the controller session (context pollution)

## Efficiency Notes

**Why fresh subagent per task:**
- Prevents context pollution from accumulated state
- Each subagent gets clean, focused context
- No confusion from prior tasks' code or reasoning

**Why two-stage review:**
- Spec review catches under/over-building early
- Quality review ensures the implementation is well-built
- Catches issues before they compound across tasks

**Cost trade-off:**
- More subagent invocations (implementer + 2 reviewers per task)
- But catches issues early (cheaper than debugging compounded problems later)

## Integration with Other Skills

### With writing-plans

This skill EXECUTES plans created by the writing-plans skill:
1. User requirements → writing-plans → implementation plan
2. Implementation plan → subagent-driven-development → working code

### With test-driven-development

Implementer subagents MUST follow TDD. The TDD Gate (Step 1.5) enforces this automatically after every implementation task. Three rules:

1. **Every implementer goal includes TDD instructions** — write failing test, verify failure, write minimal code, verify pass, commit
2. **TDD Gate runs between implementer and spec review** — verifies RED→GREEN evidence in git log, runs full test suite, checks coverage
3. **TDD_FAIL = implementation invalid** — task is re-dispatched from scratch, never patched

This upgrade from the previous integration where TDD was merely "encouraged" in context. Now it's enforced by an automated gate. See test-driven-development skill for the full TDD discipline.

### With requesting-code-review

The two-stage review process IS the code review. For final integration review, use the requesting-code-review skill's review dimensions.

### With systematic-debugging

If a subagent encounters bugs during implementation:
1. Follow systematic-debugging process
2. Find root cause before fixing
3. Write regression test
4. Resume implementation

## Example Workflow

```
[Read plan: docs/plans/auth-feature.md]
[Create todo list with 5 tasks]

--- Task 1: Create User model ---
[Dispatch implementer subagent]
  Implementer: "Should email be unique?"
  You: "Yes, email must be unique"
  Implementer: 
    git log shows: 
      test: add User model tests → FAIL (module missing)
      feat: add User model with bcrypt hash → PASS
    3/3 tests passing, committed.

[Dispatch TDD Gate]
  TDD Gate: ✅ TDD_PASS
    - test commit BEFORE feat commit ✓
    - All 3 tests pass ✓
    - No regressions ✓
    - Tests exercise real behavior ✓

[Dispatch spec reviewer]
  Spec reviewer: ✅ PASS — all requirements met

[Dispatch quality reviewer]
  Quality reviewer: ✅ APPROVED — clean code, good tests

[Mark Task 1 complete]

--- Task 2: Password hashing ---
[Dispatch implementer subagent]
  Implementer: No questions, implemented, 5/5 tests passing.
    git log: feat: add password hashing (test+impl in one commit)

[Dispatch TDD Gate]
  TDD Gate: ❌ TDD_FAIL
    - No separate test-before-code commit
    - Combined commit message doesn't state "RED→GREEN, test written first"
    - Cannot verify tests failed before implementation

[Re-dispatch implementer with strict TDD]
  Implementer: 
    git log shows:
      test: add password hashing tests → FAIL
      feat: add bcrypt hashing + validation → PASS
    7/7 tests passing.

[Dispatch TDD Gate again]
  TDD Gate: ✅ TDD_PASS

[Dispatch spec reviewer]
  Spec reviewer: ❌ Missing: password strength validation (spec says "min 8 chars")

[Implementer fixes]
  Implementer: 
    test: add password strength validation test → FAIL
    feat: add MIN_PASSWORD_LENGTH validation → PASS
    9/9 tests passing.

[Dispatch TDD Gate again]
  TDD Gate: ✅ TDD_PASS

[Dispatch spec reviewer again]
  Spec reviewer: ✅ PASS

[Dispatch quality reviewer]
  Quality reviewer: Important: Magic number 8, extract to constant
  Implementer: 
    refactor: extract MIN_PASSWORD_LENGTH constant → PASS
    9/9 tests passing.

[Dispatch TDD Gate on refactor]
  TDD Gate: ✅ TDD_PASS (refactor-only — test count unchanged, all pass ✓)

[Dispatch quality reviewer again]
  Quality reviewer: ✅ APPROVED

[Mark Task 2 complete]

... (continue for all tasks)

[After all tasks: dispatch final integration reviewer]
[Run full test suite: all passing]
[Done!]
```

## Remember

```
Fresh subagent per task
Three gates every time: TDD → Spec → Quality
TDD gate FIRST — no skipping
Spec compliance SECOND
Code quality THIRD
Never skip gates
Catch issues early
```

**Quality is not an accident. It's the result of systematic process.**

## Further reading (load when relevant)

When the orchestration involves significant context usage, long review loops, or complex validation checkpoints, load these references for the specific discipline:

- **`references/context-budget-discipline.md`** — Four-tier context degradation model (PEAK / GOOD / DEGRADING / POOR), read-depth rules that scale with context window size, and early warning signs of silent degradation. Load when a run will clearly consume significant context (multi-phase plans, many subagents, large artifacts).
- **`references/gates-taxonomy.md`** — The four canonical gate types (Pre-flight, Revision, Escalation, Abort) with behavior, recovery, and examples. Load when designing or reviewing any workflow that has validation checkpoints — use the vocabulary explicitly so each gate has defined entry, failure behavior, and resumption rules.

Both references adapted from gsd-build/get-shit-done (MIT © 2025 Lex Christopherson).

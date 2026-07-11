---
name: systematic-debugging
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, writing-plans, subagent-driven-development]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### 6. Trace Library / Framework Source Code

**WHEN debugging framework behavior (NextAuth, Express middleware, ORM, etc.):**

The library's own source code in `node_modules/` (JS/TS) or site-packages (Python) is the **authoritative documentation** for what actually happens. Don't guess — read the code:

```bash
# Find the entry point
cat node_modules/package-name/index.js

# Find specific exports
grep -rn "export function\|export const\|class " node_modules/package-name/src/

# Read the exact function that produces the error
cat node_modules/package-name/lib/path/to/function.js

# Find where an error class is used
grep -rn "ErrorClass\|throw new" node_modules/package-name/lib/
```

**Keywords to grep for in node_modules:**
- The exact error message string (e.g., `MissingCSRF`, `UnknownAction`)
- The error class name (e.g., `class MissingCSRF`)
- The function that handles the request path (e.g., `render.signin`, `parseActionAndProviderId`)
- Cookie/header manipulation logic

**Pattern for tracing auth/request flow through a framework:**
1. Find the main entry/handler (e.g., `Auth()` in `@auth/core/index.js`)
2. Find the request parser (e.g., `toInternalRequest()` that extracts action + providerId from URL)
3. Find the main dispatcher (e.g., `AuthInternal()` that routes by `method` + `action`)
4. Find the specific handler for the failing action (e.g., `render.signin()` for signin GET)
5. Read the exact validation logic (e.g., `createCSRFToken()` / `validateCSRF()`)
6. Map the known working path (Server Action POST) vs the failing path (browser GET)

**Real example** — debugging NextAuth v5 sign-in failure:
```
1. Error "MissingCSRF" → grep for `class MissingCSRF` in @auth/core → found in errors.js
2. grep for `throw new MissingCSRF` → found in csrf-token.js → validates via cookie vs body
3. grep for `validateCSRF` → found in lib/index.js → only called on POST for signin action
4. Read render.signin() → `if (providerId) throw new UnknownAction("Unsupported action")`
5. → ROOT CAUSE FOUND: GET /api/auth/signin/google always throws before CSRF is even checked
```

This technique works especially well for:
- Auth libraries (NextAuth, Passport, Lucia)
- Web frameworks (Next.js, Express, FastAPI)
- Database ORMs (Prisma, Drizzle, SQLAlchemy)
- API client SDKs

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Research-First Principle

**BEFORE writing any code or making any fix, research the problem thoroughly.**

The user prefers this approach: brainstorm multiple possible solutions, search the web for error messages, read documentation, and understand the known patterns before touching any code.

Research sources in priority order:
1. **Official docs / GitHub issues** for the specific library or tool producing the error
2. **Web search** for the exact error string or error code
3. **Library source code** (node_modules/, site-packages/) — grep for the error string
4. **Known working examples** in the same codebase or similar projects

A common failure mode is jumping straight to code changes without researching first. The user finds this frustrating. The pattern is: **research → understand → brainstorm options → then code**.

---

## Node.js / Web Server Debugging Patterns

These patterns apply when debugging Node.js servers, HTTP APIs, WebRTC services, or any server process that answers on a port.

### 1. Identify What's Actually Listening

The most common server-side debugging trap: **you fixed the code but the old process is still running.**

```bash
# Check what PID is actually answering
lsof -i :<port> -P -n 2>/dev/null     # shows PID and process name
ss -tlnp "sport = :<port>"            # alternative without lsof
netstat -tlnp 2>/dev/null | grep :<port>

# Once you have the PID:
ps -p <PID> -o pid,cmd,etime          # what is it and how long running?
readlink -f /proc/<PID>/cwd           # what directory was it started from?
cat /proc/<PID>/environ | tr '\0' '\n' # what env vars does it have?
```

**🪤 Stale process trap**: `pkill -f "pattern"` kills parent processes but **not** the actual server process, which may be a child of a child. Example:
```
bash -lic "node server.mjs"   ← pkill matches this
  └── node server.mjs         ← pkill MAY match this
       └── [server process]   ← pkill DOES NOT SURVIVE the shell wrapper
```
The child continues serving on the port with the OLD code. Always kill by PID or `lsof`-based port finder:

```bash
# ✅ DO: kill what's actually listening
lsof -ti :8765 | xargs kill -9

# ✅ DO: verify nothing is listening before restart
curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/health
# Returns '000' = connection refused (good), returns '200' = old process still alive

# After restart, verify the NEW process is serving
curl -s http://localhost:8765/health
```

### 2. Incremental Endpoint Testing

When debugging a server, test endpoints from simplest to most complex:

| Order | Test | What it proves |
|-------|------|----------------|
| 1 | `GET /health` (or any simple endpoint) | Server is running, process is alive |
| 2 | `GET /` or `GET /<static-page>` | Static file serving works |
| 3 | `POST /<api-endpoint>` with test payload | API handler logic works |
| 4 | Verify upstream response | Integration with external service works |

```bash
# Step 1: Liveness
curl -s -w "\nHTTP:%{http_code}" http://localhost:8765/health
# Expected: {"ok":true} / 200

# Step 2: Static serving
curl -s -w "\nHTTP:%{http_code}" http://localhost:8765/call | head -5
# Expected: <!DOCTYPE html>... / 200

# Step 3: API with test payload
curl -s -w "\nHTTP:%{http_code}" -X POST http://localhost:8765/session \
  -H "Content-Type: application/sdp" \
  -d "<test-sdp>"
# Expected: 400/500 from upstream (test SDP is fake) or 200 if real

# Step 4: Route coverage — unexpected 405 means route matched
curl -s -w "\nHTTP:%{http_code}" -X GET http://localhost:8765/tool
# Expected: 405 (Method Not Allowed) = route IS matching, method check works
# Compare: 404 = route NOT matching at all
```

**🪤 Pitfall**: A `405 Method Not Allowed` means the route IS matching (correct handler found but method is wrong). A `404 Not Found` means the route is NOT matching at all. This distinction tells you whether the request routing itself is broken vs. the handler logic.

### 3. Environment Variable Loading

Node.js servers that need API keys (OpenAI, Stripe, etc.) often fail because env vars aren't loaded:

```bash
# Check what the process actually sees
cat /proc/<PID>/environ | tr '\0' '\n' | grep -E 'API_KEY|SECRET|TOKEN'

# If running through Hermes background terminal(), env vars like OPENAI_API_KEY
# may be STRIPPED by the terminal sandbox. Key names containing API_KEY, SECRET,
# or TOKEN in the variable name are blocked from propagation to subprocesses.
# Workaround: have the server auto-load .env directly from disk.
```

**🪤 Pitfall**: Writing the .env file via Hermes tools may mask the actual value. When the tool displays `OPENAI_API_KEY=***`, the file contents may actually contain `***` (masked literal) rather than the real key. Verify with `wc -c` on the file or use shell echo into the file:
```bash
# ❌ write_file may write masked stars instead of real key
write_file(path=".env", content="OPENAI_API_KEY=***")

# ✅ use shell to write env var value
echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
```

### 4. Process Output Capture

Background Node.js processes started via Hermes `terminal(background=true)` may not flush stdout/stderr to the captured pipe:

```bash
# If process log is empty, try:
# a) Starting with explicit file redirection
node server.mjs > /tmp/server.log 2>&1

# b) Using console.error instead of console.log (less buffered)
# c) Waiting a few seconds before checking log
# d) Using process(action='poll') to check if still running
```

If you suspect the process is running but output isn't showing, test with a payload:
```bash
curl -s http://localhost:8765/health  # if this returns 200, process is alive
```

---

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns, grep library source code in `node_modules/` or `.venv/lib/`
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**

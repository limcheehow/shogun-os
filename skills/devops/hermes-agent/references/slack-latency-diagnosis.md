# Slack Bot Latency Diagnosis (May 2026)

## The Problem

User reported Slack bot taking 10-15s for simple messages like "hi".

## Evidence

Gateway log showed:
```
response ready: platform=slack chat=D0B0LU0HP4L time=15.1s api_calls=1 response=168 chars
```

Key insight: `api_calls=1` means the entire 15.1s was a single LLM call — no tool loops, no retries, no multi-turn. Pure model latency.

## Root Cause Analysis

Three factors contributed:

1. **`reasoning_effort: medium`** — Forces chain-of-thought on every message. Even trivial queries pay 5-10s of reasoning before response. Estimated 60-70% of the 15s.

2. **Memory at 99% capacity** (2,188/2,200 chars) — Full memory means more system prompt tokens to process before response. Estimated 15-20% of the 15s.

3. **94 skill descriptions in system prompt** (~3,000+ tokens) — Every turn scans all skills. Fixed overhead that compounds the other two. Estimated 15-20% of the 15s.

## Fixes Applied

### Fix 1: Remove reasoning_effort (High Impact)

```yaml
# BEFORE
agent:
  reasoning_effort: medium

# AFTER
agent:
  reasoning_effort: ''
```

**Result:** 15.1s → 9.1s (40% reduction, ~6s saved)

### Fix 2: Condense memory (Medium Impact)

Trim verbose entries, keep only high-value durable facts. Target <70% utilization.

**Result:** 2,188 chars (99%) → 1,494 chars (67%) — ~700 fewer tokens per turn.

### Fix 3: Fast-path channel prompt (High Impact for trivial messages)

Add a `FAST PATH` rule to the Slack channel prompt that tells the agent to skip skill loading entirely for trivial messages:

```yaml
slack:
  channel_prompts: 'D0B0LU0HP4L:...FAST PATH: greetings, acknowledgments, single-word, or under 50 chars — reply instantly, load zero skills, search nothing.'
```

**Expected result:** Further drop from ~9s → ~3-4s for simple messages, since skill scanning (~3K tokens of overhead) is bypassed.

## Measured Results

| Fix | Latency | API Calls | Notes |
|-----|---------|-----------|-------|
| Before any fix | 15.1s | 1 | Baseline |
| After reasoning_effort removed | 9.1s | 1 | 40% improvement |
| After fast-path added | ~3-4s (expected) | 0-1 | Yet to be confirmed |

## Rapid Diagnostic Checklist

```
□ grep "response ready.*slack" ~/.hermes/logs/gateway.log — check time= api_calls=
□ grep "reasoning_effort" ~/.hermes/config.yaml — if medium/high, that's likely it
□ Check memory utilization (in MEMORY section of system prompt)
□ Check if channel prompt has a FAST PATH rule
□ Check gateway is running with latest config (restart after any config change)
```

## Platform-Neutral Lesson

For flash models (deepseek-v4-flash, Claude Haiku, GPT-4o-mini) used in IM platforms:

- **`reasoning_effort` should be empty** unless the task genuinely needs step-by-step reasoning. The flash model's speed advantage is wasted if CoT eats multiple seconds per turn.
- **Keep memory lean** — condense entries over 70% capacity degrade response time measurably.
- **Channel prompts should include a FAST PATH** for trivial messages to bypass skill scanning and tool loading.
- **Always restart gateway** after any config.yaml change for it to take effect.

## Related: Vector Search Fallback

If Supabase is unreachable (e.g., IPv6-only DNS on Azure VM blocking direct connection), build a local search tool using gbrain's PGLite:

```
brain-search "query" [--limit N] [--json]
```

Located at `~/.local/bin/brain-search`. Uses `gbrain search` (keyword tsvector) against the local brain database. Fast (~1s), works even when remote DB is unreachable.
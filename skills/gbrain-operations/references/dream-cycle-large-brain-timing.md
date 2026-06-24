# Dream Cycle Timing on Large Brains (30K+ pages)

## Observed behavior (gbrain v0.42.53.0)

This user's brain has ~32,759 pages. The `gbrain dream` cycle was tested on 2026-06-25:

| Phase | Runtime | Status |
|-------|---------|--------|
| lint | <1s | ✅ immediate |
| backlinks | <1s | ✅ immediate |
| sync | <1s | ✅ immediate (no changes) |
| synthesize | <1s | ✅ skipped (no corpus) |
| extract | <1s | ✅ immediate |
| extract_facts | <1s | ✅ immediate |
| resolve_symbol_edges | <1s | ✅ immediate |
| **patterns** | **~20+ minutes** | ❌ timed out at 600s |
| embed | 1.7s (3 chunks) | ✅ fast (incremental) |
| orphans | 0.2s | ✅ fast (31,764 orphans) |

## Key takeaways

1. **Patterns is the only bottleneck.** All other phases complete in <1s on incremental cycles.
2. **First patterns run after config change is the slowest.** Once cached, subsequent runs may be faster — but on a brain this size, even cached patterns takes significant time.
3. **600s foreground timeout will always kill patterns** on this brain.
4. **The background approach works** — `terminal(background=true, notify_on_complete=true, timeout=3600)` allows the phase to run unblocked.

## Config note

The run emitted:
```
[models] deprecated config "dream.synthesize.model" ignored;
"models.dream.synthesize" is set and wins. Remove "dream.synthesize.model"
from your config in v0.30.
```
The old key `dream.synthesize.model` should be deleted from the DB config.
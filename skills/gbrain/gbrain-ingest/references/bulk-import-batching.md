# Bulk Directory Import — Subagent Batching Pattern

When importing hundreds or thousands of files via `gbrain import <dir>`, the default
`--workers` setting can exhaust system RAM. The subagent batching pattern splits the
work into smaller chunks, each handled by a single-worker subagent, with Hermes
`max_concurrent_children` acting as the throttle.

## When To Use

- Importing 500+ files in one directory
- System has < 32GB RAM
- Prior import attempts crashed with OOM or 14GB+ RSS
- You want to interleave entity extraction / cross-linking per file (not just raw parse→chunk)

## Architecture

```
N files → M batches (~200 files each) → 3 concurrent subagents
  ├── Each subagent: gbrain import <batch_dir> --no-embed --workers 1 --fresh
  ├── Memory: ~500MB per subagent (vs potentially 8-14GB with default workers)
  └── Throttled by max_concurrent_children in config.yaml (default: 3)
```

## Step-by-Step

### 1. Split files into batch directories

Use **hardlinks** (`os.link`) or copies — NOT symlinks. gbrain's `collectSyncableFiles`
walker explicitly skips symlinks as a defense against symlink cycles, and there is no
override flag.

```python
import os

SRC = "/path/to/source/dir"
DST = "/path/to/batches"
BATCH_SIZE = 200

os.makedirs(DST, exist_ok=True)
files = sorted([f for f in os.listdir(SRC) if f.endswith('.md')])

for batch_num, i in enumerate(range(0, len(files), BATCH_SIZE), start=1):
    batch_dir = os.path.join(DST, f"batch-{batch_num:03d}")
    os.makedirs(batch_dir)
    for f in files[i:i + BATCH_SIZE]:
        os.link(os.path.join(SRC, f), os.path.join(batch_dir, f))
```

### 2. Verify import state first

Check if files are already in the brain before launching:

```bash
gbrain stats          # total pages, email count
ls ~/.hermes/gbrain-home/import-checkpoint.json  # prior progress
```

The import has content-hash dedup — re-running on already-imported files safely returns
"skipped (unchanged)". But checking first saves subagent token cost.

### 3. Spawn subagents in waves

Use `delegate_task` in batch mode (up to 3 tasks per call, matching `max_concurrent_children`):

```
Wave 1: batches 001-003 (3 subagents)
  → wait for all to complete
Wave 2: batches 004-006
  → wait for all to complete
Wave 3: batches 007-009
  → wait for all to complete
Wave 4: batches 010-012
```

Each subagent goal:
```
Import batch-00N of email files into gbrain (190 markdown files)
```

Each subagent context includes the exact command:
```
BUN=<path-to-bun>
cd <gbrain-dir> && $BUN run src/cli.ts import <batch-dir> --no-embed --workers 1 --fresh
```

### 4. Verify completion

```bash
# Count pages created in the import window
gbrain stats

# Spot-check a few slugs
gbrain get <slug>
```

## Pitfalls

- **Symlinks are silently skipped** — the import walker skips them with `[gbrain import] Skipping symlink: ...`. Always use hardlinks or copies.
- **`max_concurrent_children` is the throttle** — spawning more than 3 tasks in one `delegate_task` call will queue extras. Check `delegation.max_concurrent_children` in config.yaml.
- **Subagents have NO memory of the parent conversation** — all context (bun path, gbrain dir, batch dir, command flags) must be in the `context` field.
- **Content-hash dedup is per-file** — if a file was imported, modified, and re-imported, it creates a NEW version. But identical content → "skipped (unchanged)".
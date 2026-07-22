# sync-personal-brain.sh

Location: `~/.hermes/scripts/sync-personal-brain.sh`

Daily cron job that imports the `~/personal-brain/` git repo into gbrain for voice agent access.

## Pipeline

1. **Git pull** from `https://github.com/limcheehow/personal-brain` (master)
2. **gbrain import** companies/ (~4,500 files) — longest phase
3. **gbrain import** deals/ (~200 files) — sales pipeline
4. **gbrain import** people/ (~6,500 files) — second longest phase
5. **gbrain import** meetings/ (~40 files)
6. **gbrain import** projects/ (~7 files)
7. **gbrain embed --stale** — generates embeddings for new/changed pages

## Config

```
GBRAIN_EMBEDDING_MODEL=openai:text-embedding-3-large
GBRAIN_EMBEDDING_DIMENSIONS=1536
```

## Runtime

- Total: ~2-2.5 hours for ~11,000 files
- Must run in background with `notify_on_complete=true` (foreground 300s timeout kills it)
- Log: `~/.hermes/scripts/sync-personal-brain.log`
- Progress lines: `[import.files] N/TOTAL (P%) imported=N skipped=S errors=E`
- Skipped files = already up-to-date in gbrain (idempotent)

## Log Sample

```
[2026-06-12 06:00:54] Starting personal-brain sync...
  Importing companies...
[import.files] 505/5047 (10%) imported=505 skipped=0 errors=0
  Importing deals...
[import.files] 12/210 (5%) imported=12 skipped=0 errors=0
  Importing people...
...
  Embedding new content...
[2026-06-12 08:15:00] Sync complete.
```

## Cron

Run daily via `hermes cron`. Should use `--deliver origin` to report results back to the creating chat, or `--deliver local` for silent operation. `--no-agent` is also viable since the script's stdout is self-describing.
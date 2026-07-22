# Cron Job `--script` Path Pitfall — Real Session

## The Error

The cron job "your-product V2 Notion + GitHub Sync" was created with:

```
hermes cron create '0 3 * * *' --name 'your-product V2 Sync' --script 'cd ~/.hermes/sync && python3 notion-brain-sync.py 2>&1' --deliver origin
```

The `--script` parameter received an inline shell command instead of a file path. At runtime the scheduler reported:

```
Script not found: /home/tapway/.hermes/scripts/cd ~/.hermes/sync && python3 notion-brain-sync.py 2>&1
```

Hermes treats the entire `--script` value as a file path relative to `~/.hermes/scripts/`. Whitespace, `&&`, and redirects (`2>&1`) are part of the filename — not shell syntax.

## Diagnosis

1. Listed cron jobs with `hermes cron list` — found job ID `a675efba6f33`
2. Observed `Script: cd ~/.hermes/sync && python3 notion-brain-sync.py 2>&1` — clearly a command, not a path
3. Verified the actual script existed at `~/.hermes/sync/notion-brain-sync.py`

## Fix Applied

1. Created a wrapper script at `~/.hermes/scripts/your-product-v2-sync.sh`:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   cd "$HOME/.hermes/sync"
   python3 notion-brain-sync.py
   ```
2. Made it executable: `chmod +x ~/.hermes/scripts/your-product-v2-sync.sh`
3. Updated the cron job:
   ```bash
   hermes cron edit a675efba6f33 --script your-product-v2-sync.sh
   ```
4. Verified the wrapper works: `bash ~/.hermes/scripts/your-product-v2-sync.sh` — sync completed successfully.

## Key Lesson

Always create a `.sh` wrapper script in `~/.hermes/scripts/` for any cron job that needs shell commands (cd, redirects, pipes, &&). The `--script` parameter only accepts file paths — never inline shell commands.

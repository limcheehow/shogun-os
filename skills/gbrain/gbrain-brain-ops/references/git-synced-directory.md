# Git-synced brain directory — production reference

This reference documents the `~/brain/projects/` setup as a concrete example of integrating an external git repo into a brain subdirectory with two-way sync.

## Repo details

| Field | Value |
|-------|-------|
| Remote | `https://github.com/tapway/tapway-project-brain.git` |
| Local path | `~/brain/projects/` |
| Cron job | `tapway-project-brain-sync` (job_id: b64f00c8808c) |
| Sync schedule | 6am & 6pm daily |
| Script | `~/.hermes/scripts/sync-project-brain.sh` |

## .gitignore pattern

```gitignore
/*
!/projects/
!/active_projects/
!/support_tickets/
!/scripts/
!.gitignore

# OS junk files
**/desktop.ini
**/Thumbs.db
**/.DS_Store

# Temp files from filesystem operations
**/.fuse_hidden*

# Sync script log
scripts/sync-brain.log
```

The first line (`/*`) ignores everything. Then `!/` lines selectively un-ignore only the directories that should be tracked by git. Any directory not listed (e.g. `haiku/`, `jinzai/`, `your-product/`, `your-product-v2/`) stays local-only.

## Sync script

```bash
#!/usr/bin/env bash
# Synchronise ~/brain/projects/ with company-project-brain (two-way)
set -euo pipefail

REPO_DIR="$HOME/brain/projects"
COMMIT_AUTHOR="Hermes Agent <hermes@example.com>"

cd "$REPO_DIR"

# Fetch remote state
git fetch origin 2>&1

# Check if we're behind (remote has new commits)
BEHIND=$(git rev-list --count HEAD..origin/master 2>/dev/null || echo "0")
AHEAD=$(git rev-list --count origin/master..HEAD 2>/dev/null || echo "0")

# Stage any local changes (new or modified files in tracked dirs)
if [ -n "$(git status --porcelain)" ]; then
    echo "Local changes detected. Staging and committing..."
    git add -A
    git commit -m "Daily sync - $(date '+%Y-%m-%d %H:%M')" --author="$COMMIT_AUTHOR"
    AHEAD=$(git rev-list --count origin/master..HEAD 2>/dev/null || echo "0")
fi

# Two-way sync: pull rebase first, then push
if [ "$BEHIND" -gt 0 ] || [ "$AHEAD" -gt 0 ]; then
    if ! git pull --rebase origin master 2>&1; then
        echo "CONFLICT DETECTED during rebase!"
        git rebase --abort 2>/dev/null || true
        echo "SYNC FAILED - conflicts need manual resolution"
        exit 1
    fi

    if git push origin master 2>&1; then
        echo "Sync completed successfully."
    else
        echo "Push failed. Check git log and retry."
        exit 1
    fi
else
    echo "Already up to date."
fi
```

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| Standalone nested git repo | Submodules require the parent brain repo (`~/brain/`) to pin a ref. A standalone `.git` dir is invisible to the parent and avoids "dirty submodule" warnings. |
| `git pull --rebase` | Linear history. Local commits sit on top of remote commits. No merge bubbles. |
| Conflict: abort + exit (not retry) | Conflicts in project data are semantic — they need a human to decide. Silent retry would risk data loss. |
| Auto-commit with timestamp | Ensures every change is captured even if the agent forgets to commit. Author name distinguishes bot from human. |
| `deliver: local` on cron | Silent on success. The user only hears about it if something actually happened (or broke). |

## Cron job creation reference

Created via the `cronjob` tool (not `hermes cron create` CLI):

```json
{
  "action": "create",
  "name": "tapway-project-brain-sync",
  "schedule": "0 6,18 * * *",
  "script": "sync-project-brain.sh",
  "deliver": "local",
  "prompt": "Run the project brain sync..."
}
```

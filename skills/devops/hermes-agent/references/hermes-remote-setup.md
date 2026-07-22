---
name: hermes-remote-setup
description: Clone/duplicate a Hermes installation to a remote GPU/cloud server — brain via git, profiles via rsync, config/secrets via scp, bootstrap script. Use when setting up Hermes on any new machine.
category: devops
tags: [hermes, remote, deployment, gpu, cloud, setup, sync, git, rsync]
---

# Hermes Remote Setup — Duplicate to a Cloud/GPU Server

Load this skill when setting up Hermes on a remote machine (GPU cloud server, second VM, etc.) and you need to duplicate profiles, brain, skills, and config from an existing installation.

## Core Strategy: Two-Path Sync

| Asset | Method | Why |
|---|---|---|
| `~/brain/` | **git** (push/pull) | Version history, easy sync, no stale copies |
| `~/.hermes/profiles/` | **rsync** (one-time, then rare) | 7+ profiles with memories, SOUL.md, configs |
| `~/.hermes/skills/` | **rsync** or git | Custom skills you've built |
| `~/.hermes/{.env,config.yaml,auth.json}` | **scp** | Secrets and model config |
| `~/.git-credentials` | Skip | Machine-specific auth |

## Step 1: Brain via Git

First, ensure the brain is in a private GitHub repo with a PII-aware `.gitignore`:

```gitignore
# Never commit
daily/
_scrum/
inbox/
data/email/
data/calendar/
people/*/kpi/

# Temp
*.bak
.DS_Store
.obsidian/
.trash/
```

Push once, then clone on the remote:

```bash
# On remote GPU server
git clone https://github.com/tapway/tapway-brain.git ~/brain
```

Ongoing: `git push` from WSL, `git pull` on remote.

## Step 2: Profiles & Skills Sync

**Direction matters.** If the remote can reach your local machine, use **pull** (rsync/scp from remote). If your local machine can reach the remote but not vice versa (common when local is behind NAT/WSL), use **push** (paramiko/SFTP from local).

### Option A: Pull (rsync/scp from remote) — preferred when remote can SSH to you

```bash
# From the GPU server, pull from your local machine
rsync -avz user@your-local-ip:~/.hermes/profiles/ ~/.hermes/profiles/
rsync -avz user@your-local-ip:~/.hermes/skills/ ~/.hermes/skills/
scp user@your-local-ip:~/.hermes/{.env,config.yaml,auth.json} ~/.hermes/
```

**Requires:** Remote can reach your local IP (not possible if local is behind NAT/WSL).

### Option B: Push (paramiko/SFTP from local) — use when remote is reachable but local isn't

When the remote is a cloud instance with a public IP but your local machine is behind NAT/WSL, push the files:

```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("remote-ip", username="root", password="your-password")

sftp = client.open_sftp()

# Upload a directory tree (skipping sessions, logs, DB files)
def upload_dir(sftp, local_dir, remote_dir):
    for entry in os.listdir(local_dir):
        local_path = os.path.join(local_dir, entry)
        remote_path = remote_dir + "/" + entry
        if entry in ("sessions", "logs", "audio_cache", "state", "cron"):
            continue
        if os.path.isdir(local_path):
            sftp.mkdir(remote_path)  # ignore EEXIST
            upload_dir(sftp, local_path, remote_path)
        else:
            sftp.put(local_path, remote_path)

upload_dir(sftp, "~/.hermes/profiles", "/root/.hermes/profiles")
upload_dir(sftp, "~/.hermes/skills", "/root/.hermes/skills")
sftp.put("~/.hermes/config.yaml", "/root/.hermes/config.yaml")
sftp.put("~/.hermes/.env", "/root/.hermes/.env")

sftp.close()
client.close()
```

**Requires:** `pip install paramiko` on the local machine. No inbound SSH needed.

### Option C: SSH with password (sshpass)

If `sshpass` is installed, you can script password-based SSH:

```bash
sshpass -p 'password' rsync -avz ~/.hermes/profiles/ root@remote-ip:~/.hermes/profiles/
```

**Pitfall:** `sshpass` requires sudo to install on some systems. If unavailable, use Option B (paramiko).

## Step 3: Config & Secrets

See Step 2 — same direction options apply. Key files:

| File | Purpose |
|---|---|
| `~/.hermes/config.yaml` | Model, provider, platform config, toolsets |
| `~/.hermes/.env` | Bot tokens, API keys |
| `~/.hermes/auth.json` | OAuth credentials (Google, etc.) |
| `~/.hermes/supabase_key.txt` | Database service key |

## Step 4: Bootstrap & Start

```bash
pip install hermes-agent
hermes setup

# Start via tmux watchdog (same pattern as WSL)
cp ~/.hermes/skills/devops/hermes-agent/scripts/hermes-gateway-watchdog.sh ~/.local/bin/
chmod +x ~/.local/bin/hermes-gateway-watchdog.sh
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
```

## What NOT to Sync

| Skip | Why |
|---|---|
| `~/.hermes/sessions/` | Chat history doesn't transfer between gateways |
| `~/.hermes/logs/` | Pointless |
| `~/.hermes/audio_cache/` | Regenerates |
| `~/.hermes/plans/` | Stale |
| Cron jobs | Different server = different paths. Export + recreate. |

## Pitfalls

- **One bot token, one gateway** — if WSL gateway is still running, the remote gateway will fail with "token already in use." Stop one or use different bot tokens.
- **Cron job paths** — `workdir` and script paths may differ on the remote. Recreate jobs on the new machine.
- **Pre-commit hooks in brain repo** — the Company brain has a validator hook (`projects/your-product/scripts/validate-brain.py`) that blocks commits if new your-product task files are missing `task_id`, have invalid statuses, etc. Run `python3 projects/your-product/scripts/validate-brain.py` before pushing if you've added your-product files. The hook compares against a baseline at `~/.hermes/state/brain-validator-errors.txt` and only blocks NEW errors (not existing ones).
- **rsync preserves permissions** — add `--no-perms` if remote user differs.
- **Profile paths are absolute** — `~` must expand to the correct home directory on the remote.
- **Push direction needs SFTP resume** — large profile uploads (600+ files per profile, 8+ profiles) can take 2+ minutes. The default rsync/scp approach assumes the remote can pull from local, which fails when local is behind NAT/WSL. Use the paramiko push script (see `references/push-to-remote.py`). The script skips `sessions/`, `logs/`, `audio_cache/`, and `.db`/`.db-wal` files to avoid unnecessary transfer. On timeout, re-run — it skips existing files by checking `sftp.stat()`.
- **SOUL.md + config.yaml + .env require separate pass** — paramiko SFTP uploads files in directory order. SOUL.md, config.yaml, and .env may fail on first pass if the profile directory doesn't exist yet. Run a second targeted pass that creates profile dirs first, then uploads these three files per profile.

## References

- `references/remote-bootstrap.sh` — Full one-shot bootstrap script for GPU servers.
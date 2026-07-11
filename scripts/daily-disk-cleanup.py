#!/usr/bin/env python3
"""Daily disk cleanup — targets the real space eaters in WSL2.

Generic version — paths come from configurable lists. Set CLEANUP_PATHS
env var as JSON or edit the PATHS dict below.
"""
import subprocess, shutil, os, sys, json
from pathlib import Path
from datetime import datetime, timedelta

HOME = Path.home()
NOW = datetime.now()
CUTOFF_7D = NOW - timedelta(days=7)
CUTOFF_3D = NOW - timedelta(days=3)
freed_total = 0

# ── Config ──────────────────────────────────────────────────────
# Edit these paths or set the CLEANUP_PATHS environment variable
# as a JSON object (see config.yaml.example for format).
PATHS = {
    # Linux paths
    "apt_cache": "/var/cache/apt/archives",
    "pip_cache": "~/.cache/pip",
    "npm_cache_linux": "~/.npm",
    "journald": {"vacuum_size": "100M", "vacuum_time": "7d"},
    "syslog": "/var/log",
    "tmp": "/tmp",
    "cron_output": "~/.hermes/cron/output",
    "playwright_cache": "~/.cache/ms-playwright",

    # Windows paths (WSL2 /mnt/c/ mount)
    # Windows username is auto-detected, or set WINDOWS_USER env var
    "npm_cache_windows": "/mnt/c/Users/{windows_user}/AppData/Local/npm-cache",
    "wsl_crashes": "/mnt/c/Users/{windows_user}/AppData/Local/Temp/wsl-crashes",

    # Git repos to gc
    "git_repos": ["~/brain", "~/.gbrain"],
}

# Override from env var (JSON format)
if os.environ.get("CLEANUP_PATHS"):
    try:
        PATHS.update(json.loads(os.environ["CLEANUP_PATHS"]))
    except json.JSONDecodeError:
        print(f"  ⚠ CLEANUP_PATHS env var is not valid JSON, using defaults")

# Windows user auto-detect
WINDOWS_USER = os.environ.get("WINDOWS_USER", "")
if not WINDOWS_USER:
    try:
        users_dir = Path("/mnt/c/Users")
        if users_dir.exists():
            candidates = [d.name for d in users_dir.iterdir() if d.is_dir() and d.name not in ("Public", "Default", "Default User", "All Users")]
            if candidates:
                WINDOWS_USER = candidates[0]
    except Exception:
        pass

def resolve_path(p):
    """Resolve a path string, expanding ~ and {windows_user}."""
    p = p.replace("~", str(HOME))
    p = p.replace("{windows_user}", WINDOWS_USER)
    return Path(p)

def run(cmd, check=True):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if check and r.returncode != 0:
            print(f"  ⚠ {cmd[:50]}... rc={r.returncode}")
        return r.stdout.strip()
    except Exception as e:
        print(f"  ⊘ {cmd[:50]}... ({e})")
        return ""

def size(p):
    try:
        pp = resolve_path(p) if isinstance(p, str) else p
        return sum(f.stat().st_size for f in pp.rglob('*') if f.is_file())
    except Exception:
        return 0

def rm_older(path, days):
    """Remove files older than N days in a directory tree."""
    cutoff = NOW - timedelta(days=days)
    before = size(path)
    for f in resolve_path(path).rglob('*'):
        try:
            if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                os.remove(f)
        except OSError:
            pass
    after = size(path)
    return before - after

def log_action(label, before, after):
    freed = before - after
    if freed > 0:
        mb = freed / (1024*1024)
        print(f"  [{label}] Freed {mb:.1f} MB")
    return freed


print("=== Daily Disk Cleanup ===")
print(f"Time: {NOW.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ── 1. APT cache ──────────────────────────────────────────
before = size(PATHS.get("apt_cache", ""))
run('sudo apt-get clean 2>/dev/null', check=False)
after = size(PATHS.get("apt_cache", ""))
freed_total += log_action('apt cache', before, after)

# ── 2. pip cache ──────────────────────────────────────────
before = size(resolve_path(PATHS.get("pip_cache", "")))
run('pip3 cache purge 2>/dev/null', check=False)
after = size(resolve_path(PATHS.get("pip_cache", "")))
freed_total += log_action('pip cache', before, after)

# ── 3. npm cache (Linux) ────────────────────────────
before = size(resolve_path(PATHS.get("npm_cache_linux", "")))
run('npm cache clean --force 2>/dev/null', check=False)
after = size(resolve_path(PATHS.get("npm_cache_linux", "")))
freed_total += log_action('npm cache (linux)', before, after)

# ── 4. npm cache (Windows AppData) ─────────────────────────
if WINDOWS_USER:
    win_npm = resolve_path(PATHS.get("npm_cache_windows", ""))
    if win_npm.exists():
        before = size(win_npm)
        shutil.rmtree(win_npm, ignore_errors=True)
        after = size(win_npm)
        freed_total += log_action('npm cache (windows)', before, after)

# ── 5. WSL crash dumps ────────────────────────────
if WINDOWS_USER:
    wsl_crashes = resolve_path(PATHS.get("wsl_crashes", ""))
    if wsl_crashes.exists():
        before = size(wsl_crashes)
        shutil.rmtree(wsl_crashes, ignore_errors=True)
        wsl_crashes.mkdir(exist_ok=True)
        after = size(wsl_crashes)
        freed_total += log_action('wsl crash dumps', before, after)

# ── 6. Rotate syslog ─────────────────────────────────────
before = size(PATHS.get("syslog", ""))
run('sudo logrotate -f /etc/logrotate.conf 2>/dev/null', check=False)
freed = rm_older(PATHS.get("syslog", ""), 7)
after = size(PATHS.get("syslog", ""))
freed_total += max(0, after - before)
print(f"  [syslog] Rotated + removed >7d logs")

# ── 7. Journald vacuum ─────────────────────────────────────
journald_config = PATHS.get("journald", {})
vacuum_size = journald_config.get("vacuum_size", "100M") if isinstance(journald_config, dict) else "100M"
vacuum_time = journald_config.get("vacuum_time", "7d") if isinstance(journald_config, dict) else "7d"

before_mb = int(run("journalctl --disk-usage 2>/dev/null | grep -oP '\\d+' | head -1", check=False) or 0)
run(f'sudo journalctl --vacuum-size={vacuum_size} --vacuum-time={vacuum_time} 2>/dev/null', check=False)
after_mb = int(run("journalctl --disk-usage 2>/dev/null | grep -oP '\\d+' | head -1", check=False) or 0)
freed_mb = before_mb - after_mb
if freed_mb > 0:
    print(f"  [journald] Freed {freed_mb} MB")
    freed_total += freed_mb * 1024 * 1024

# ── 8. Playwright cache ─────────────────────────────────
pw_cache = resolve_path(PATHS.get("playwright_cache", ""))
before = size(pw_cache)
if pw_cache.exists():
    for d in pw_cache.iterdir():
        try:
            mtime = datetime.fromtimestamp(d.stat().st_mtime)
            if mtime < CUTOFF_7D:
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass
after = size(pw_cache)
freed_total += log_action('playwright cache', before, after)

# ── 9. Old cron output (>7 days) ──────────────────────────
cron_out = resolve_path(PATHS.get("cron_output", ""))
if cron_out.exists():
    before = size(cron_out)
    for d in cron_out.iterdir():
        try:
            if d.is_dir() and datetime.fromtimestamp(d.stat().st_mtime) < CUTOFF_7D:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass
    after = size(cron_out)
    freed_total += log_action('cron outputs', before, after)

# ── 10. Old /tmp files (>3 days) ───────────────────────────
tmp_path = resolve_path(PATHS.get("tmp", ""))
before = size(tmp_path)
for f in tmp_path.iterdir():
    try:
        if f.is_file() and not str(f.name).startswith('systemd'):
            if datetime.fromtimestamp(f.stat().st_mtime) < CUTOFF_3D:
                os.remove(f)
    except (OSError, PermissionError):
        pass
after = size(tmp_path)
freed_total += log_action('/tmp cleanup', before, after)

# ── 11. Git gc in repos ────────────────────────────────────
repos = PATHS.get("git_repos", [])
for repo_path in repos:
    repo = resolve_path(repo_path)
    if (repo / '.git').exists():
        before = size(repo / '.git')
        run(f'git -C {repo} gc --auto --quiet 2>/dev/null', check=False)
        after = size(repo / '.git')
        freed_total += log_action(f'git gc ({repo.name})', before, after)

# ── Summary ────────────────────────────────────────────────
print()
used = run("df -h / | tail -1 | awk '{print $3}'", check=False)
print(f"Disk used: {used}")
if freed_total > 0:
    print(f"TOTAL FREED: {freed_total / (1024*1024):.1f} MB")
else:
    print("Nothing needed cleaning.")
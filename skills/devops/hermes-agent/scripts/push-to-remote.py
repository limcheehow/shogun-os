#!/usr/bin/env python3
"""Push Hermes profiles, skills, config to a remote machine via SSH/SFTP.

Use when the remote has a public IP but the local machine is behind NAT/WSL
(i.e., the remote CANNOT SSH back to pull). Requires paramiko on the local machine.

Usage:
  python3 push-to-remote.py <host> <user> <password>

Edit SKIP_DIRS and SKIP_SUFFIXES below to customize what's excluded.
"""

import paramiko
import os
import sys
from pathlib import Path

if len(sys.argv) < 4:
    print("Usage: push-to-remote.py <host> <user> <password>")
    sys.exit(1)

HOST = sys.argv[1]
USER = sys.argv[2]
PASS = sys.argv[3]
REMOTE_HERMES = os.path.expanduser(f"~{USER}") + "/.hermes" if USER != "root" else "/root/.hermes"

LOCAL_HERMES = Path.home() / ".hermes"
PROFILES_DIR = LOCAL_HERMES / "profiles"
SKILLS_DIR = LOCAL_HERMES / "skills"

# What to skip
SKIP_SUFFIXES = {".db", ".db-wal", ".db-shm", ".lock"}
SKIP_DIRS = {"sessions", "logs", "audio_cache", "state", "plans", "cron"}

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=15)
    return client

def remote_exists(sftp, path):
    try:
        sftp.stat(path)
        return True
    except FileNotFoundError:
        return False

def mkdir_p(sftp, remote_path):
    try:
        sftp.stat(remote_path)
    except FileNotFoundError:
        parent = os.path.dirname(remote_path)
        if parent and parent != "/":
            mkdir_p(sftp, parent)
        sftp.mkdir(remote_path)

def upload_file(sftp, local, remote):
    try:
        sftp.put(str(local), remote)
        return True
    except Exception as e:
        print(f"  ✗ {os.path.basename(local)}: {e}")
        return False

def upload_dir(sftp, local_dir, remote_dir, skip_existing=True):
    count = 0
    for entry in sorted(os.listdir(local_dir)):
        local_path = os.path.join(local_dir, entry)
        remote_path = remote_dir + "/" + entry
        
        if entry in SKIP_DIRS:
            continue
        if any(entry.endswith(s) for s in SKIP_SUFFIXES):
            continue
        
        if os.path.isdir(local_path):
            if skip_existing and remote_exists(sftp, remote_path):
                count += 1
            else:
                mkdir_p(sftp, remote_path)
                count += upload_dir(sftp, local_path, remote_path, skip_existing)
        else:
            if not (skip_existing and remote_exists(sftp, remote_path)):
                upload_file(sftp, local_path, remote_path)
            count += 1
    return count

def main():
    print(f"Connecting to {USER}@{HOST}...")
    client = connect()
    sftp = client.open_sftp()
    ssh = client

    # 1. Root-level config files
    print("\n=== Config files ===")
    for fname in [".env", "config.yaml", "auth.json", "supabase_key.txt"]:
        local = LOCAL_HERMES / fname
        if local.exists():
            upload_file(sftp, local, f"{REMOTE_HERMES}/{fname}")

    # 2. SOUL.md + config.yaml + .env + memories per profile
    print("\n=== Profile metadata ===")
    profile_names = sorted(d for d in os.listdir(PROFILES_DIR)
                           if os.path.isdir(os.path.join(PROFILES_DIR, d)))
    for pname in profile_names:
        remote = f"{REMOTE_HERMES}/profiles/{pname}"
        mkdir_p(sftp, remote)
        for fn in ["SOUL.md", "config.yaml", ".env"]:
            lf = PROFILES_DIR / pname / fn
            if lf.exists():
                upload_file(sftp, lf, f"{remote}/{fn}")
        mem_local = PROFILES_DIR / pname / "memories"
        if mem_local.exists():
            mkdir_p(sftp, f"{remote}/memories")
            for mf in mem_local.iterdir():
                if mf.is_file():
                    upload_file(sftp, mf, f"{remote}/memories/{mf.name}")

    # 3. Full profile trees
    print("\n=== Profile files ===")
    for pname in profile_names:
        local = str(PROFILES_DIR / pname)
        remote = f"{REMOTE_HERMES}/profiles/{pname}"
        print(f"\n  {pname}/")
        n = upload_dir(sftp, local, remote, skip_existing=True)
        print(f"  → {n} items")

    # 4. Skills
    print("\n=== Skills ===")
    for sname in sorted(os.listdir(SKILLS_DIR)):
        local = str(SKILLS_DIR / sname)
        if not os.path.isdir(local):
            continue
        remote = f"{REMOTE_HERMES}/skills/{sname}"
        mkdir_p(sftp, remote)
        n = upload_dir(sftp, local, remote, skip_existing=True)
        if n > 0:
            print(f"  {sname}: {n}")

    # 5. Verify
    print("\n=== Verification ===")
    _, stdout, _ = ssh.exec_command(f"ls {REMOTE_HERMES}/profiles/")
    print(f"Profiles: {stdout.read().decode().strip()}")
    _, stdout, _ = ssh.exec_command(f"find {REMOTE_HERMES}/skills -name 'SKILL.md' | wc -l")
    print(f"Skills: {stdout.read().decode().strip()} SKILL.md files")

    sftp.close()
    client.close()
    print("\n✅ Done")

if __name__ == "__main__":
    main()
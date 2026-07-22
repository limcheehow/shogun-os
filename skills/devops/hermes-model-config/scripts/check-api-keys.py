#!/usr/bin/env python3
"""Check all Hermes profile config files for truncated API keys.

A truncated key contains literal '...' in the value (e.g. 'sk-c0b...ca38',
length=13). A 35-char key displayed as 'sk-c0b...ca38' by read_file is fine
(length=35, no '...' in actual string) — only len() distinguishes them.

Exit codes:
  0 — all keys healthy
  1 — at least one truncated key found
"""
import os
import sys
import yaml

HERMES_HOME = os.path.expanduser("~/.hermes")
profiles_dir = os.path.join(HERMES_HOME, "profiles")

configs = [os.path.join(HERMES_HOME, "config.yaml")]
if os.path.isdir(profiles_dir):
    for p in os.listdir(profiles_dir):
        configs.append(os.path.join(profiles_dir, p, "config.yaml"))

exit_code = 0
for path in configs:
    if not os.path.isfile(path):
        continue
    try:
        with open(path) as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        profile = os.path.basename(os.path.dirname(path))
        print(f"⚠ [{profile}] Could not parse: {e}")
        continue

    profile = os.path.basename(os.path.dirname(path)) if "profiles" in path else "default"
    model_key = cfg.get("model", {}).get("api_key", "")
    if "..." in model_key:
        print(f"✗ [{profile}] MODEL api_key TRUNCATED: len={len(model_key)}, contains '...'")
        exit_code = 1
    else:
        print(f"✓ [{profile}] MODEL api_key: len={len(model_key)}, ok")

    custom_providers = cfg.get("custom_providers", [])
    if isinstance(custom_providers, list):
        for i, cp in enumerate(custom_providers):
            cp_key = cp.get("api_key", "")
            name = cp.get("name", f"#{i}")
            if "..." in cp_key:
                print(f"✗ [{profile}] CUSTOM '{name}' api_key TRUNCATED: len={len(cp_key)}, contains '...'")
                exit_code = 1
            else:
                print(f"✓ [{profile}] CUSTOM '{name}' api_key: len={len(cp_key)}, ok")

sys.exit(exit_code)
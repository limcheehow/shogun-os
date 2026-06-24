# Python Wrapper Pattern for gbrain CLI

## Problem

The OpenRouter API key in `~/.hermes/.env` often contains characters (`$`, `"`, backticks,
etc.) that break bash shell escaping. Commands like:

```bash
OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) ...
```

fail silently or with syntax errors when the key has special characters, especially when
wrapped in `bash -c` (required for `terminal(background=true)`).

## Solution: Python Wrapper

`~/.hermes/scripts/gbrain-runner.py` reads the API key safely via Python file I/O and
passes it as environment variables to a subprocess. Args pass through transparently.

```python
#!/usr/bin/env python3
"""Run gbrain command with env vars injected safely. Args pass through."""
import subprocess, os, sys

home = os.environ["HOME"]
env_path = os.path.join(home, ".hermes", ".env")
key = None
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY=*** and not line.startswith("#"):
                key = line.split("=", 1)[1]
                break

if not key:
    print("ERROR: OPENROUTER_API_KEY not found", file=sys.stderr)
    sys.exit(1)

env = os.environ.copy()
env["OPENROUTER_API_KEY"] = key
env["OPENAI_API_KEY"] = key
env["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

result = subprocess.run(
    ["bun", "run", "src/cli.ts"] + sys.argv[1:],
    cwd=os.path.join(home, "gbrain"),
    env=env,
    capture_output=False,
    text=True,
)
sys.exit(result.returncode)
```

## Usage

```bash
# Dream cycle
python3 ~/.hermes/scripts/gbrain-runner.py dream

# Dry-run
python3 ~/.hermes/scripts/gbrain-runner.py dream --dry-run

# Embed stale
python3 ~/.hermes/scripts/gbrain-runner.py embed --stale

# Think with save
python3 ~/.hermes/scripts/gbrain-runner.py think "question" --save
```

## For background execution

```bash
# In terminal(background=true, notify_on_complete=true):
python3 /home/cheehow/.hermes/scripts/gbrain-runner.py dream 2>&1

# Or in a cron script:
```bash
python3 /home/cheehow/.hermes/scripts/gbrain-runner.py embed --stale
```

The wrapper works in background mode because Python handles the env vars before spawning
the subprocess — no shell escaping involved.
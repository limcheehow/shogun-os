# DashScope Embedding Migration (OpenRouter → DashScope)

When migrating a script from OpenRouter/OpenAI embeddings to DashScope without changing the Supabase vector dimensions.

## Problem

A script uses OpenRouter to call `text-embedding-3-large` (1536-dim). Moving to DashScope means no OpenRouter key needed, but DashScope doesn't have `text-embedding-3-large`.

## Solution

Use DashScope's `text-embedding-v4` with the `dimensions` parameter to force 1536-dim output:

```python
from openai import OpenAI
import yaml

cfg = yaml.safe_load(open("~/.hermes/config.yaml"))
client = OpenAI(
    api_key=cfg["model"]["api_key"],
    base_url=cfg["model"]["base_url"],  # DashScope compatible endpoint
)
resp = client.embeddings.create(
    model="text-embedding-v4",
    input=text,
    dimensions=1536,  # ← match existing Supabase vector(1536) column
)
```

No Supabase schema migration needed — the vector column stays `vector(1536)`.

## Verifying model availability

DashScope's `/v1/models` endpoint lists available models:

```python
models = client.models.list()
embed_models = [m.id for m in models if 'embed' in m.id.lower()]
# → ['text-embedding-v4', 'text-embedding-v3']
```

Both `text-embedding-v4` and `text-embedding-v3` support custom dimensions (tested: 1024 and 1536).

## Migration steps for supabase-sync-v2.py

1. Replace `get_client()` to read from config.yaml instead of `/tmp/openrouter_key.txt`:
```python
def get_client():
    cfg = yaml.safe_load(open(os.path.expanduser("~/.hermes/config.yaml")))
    return OpenAI(
        api_key=cfg["model"]["api_key"],
        base_url=cfg["model"]["base_url"],
    )
```

2. Change model + add dimensions:
```python
EMBEDDING_MODEL = "text-embedding-v4"
DIMENSIONS = 1536

resp = client.embeddings.create(
    model=EMBEDDING_MODEL, input=text, dimensions=DIMENSIONS
)
```

3. Keep `match_pages` SQL using `vector(1536)` — no change needed.

## Pitfall: `/tmp/` files are volatile

Never store API keys in `/tmp/`. The cron scheduler runs in a clean environment where `/tmp/` may be empty. Read from config.yaml or environment variables instead.
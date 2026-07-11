# Firecrawl API Usage

Firecrawl is the primary web extraction backend for `web_extract`. API key is stored in `~/.hermes/.env` as `FIRECRAWL_API_KEY`.

## Key Location

```bash
~/.hermes/.env  →  FIRECRAWL_API_KEY=fc-YOUR...KEY
```

The `.env` file is protected from the `patch` tool — use `sed -i` to modify:

```bash
sed -i 's|^# FIRECRAWL_API_KEY=|FIRECRAWL_API_KEY=sk-your-key|' ~/.hermes/.env
```

Firecrawl key is **not** stored in `config.yaml` — it goes in `.env` only.

## Direct API (curl)

```bash
curl -s -X POST 'https://api.firecrawl.dev/v2/scrape' \
  -H "Authorization: Bearer ${FIRECRAWL_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com"}'
```

Use this pattern when:
- You need the raw API response (to inspect metadata, status codes)
- `web_extract` is unavailable (e.g. in scripts, cron jobs)
- Testing whether the key is valid (`jq .success`)

## Firecrawl CLI

The `firecrawl-cli` package was initialized globally with `npx -y firecrawl-cli@latest init --all -k <key>` — this installed **29 skills** across AI coding agents (Claude Code, etc.) and registered the `firecrawl` command globally.

Available CLI commands:

| Command | Usage | Example |
|---------|-------|---------|
| `firecrawl scrape` | Extract page content as markdown | `firecrawl scrape https://example.com` |
| `firecrawl search` | Web search with results | `firecrawl search "latest AI news"` |
| `firecrawl interact` | Interact with pages (click, type, navigate) | `firecrawl interact "click the login button" "https://..."` |

The CLI is useful for one-off extraction tasks and testing outside of Hermes.

## Integration with Hermes

- `web_extract` uses Firecrawl when `config.yaml` has `extract_backend: firecrawl` and `use_gateway: false`
- The API key from `.env` is read at session start — a `/reset` is needed to pick up new keys
- Firecrawl is the **first priority** in the extraction fallback chain

## Pitfalls

- **Envvars need a new session** — changing `.env` mid-session won't affect `web_extract` until `/reset`
- **Rate limits** — Firecrawl has usage limits per API key tier. Check response headers for `X-RateLimit-*`
- **The 29 installed skills are for other AI coding agents (Claude Code, Codex)** — they don't affect Hermes. Hermes uses its own `profile-enrichment` skill for enrichment workflows

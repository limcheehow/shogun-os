# MCP-Based Web Search & Scraping (Exa + Firecrawl)

Hermes' native MCP client can connect to Exa and Firecrawl MCP servers for real web search, scraping, and content extraction — far more powerful than the legacy DuckDuckGo `web_search` backend.

## Why MCP over legacy `web_search`

| Feature | Legacy `web_search` (ddgs) | MCP (Exa + Firecrawl) |
|---|---|---|
| Search quality | Raw DuckDuckGo results | Exa's semantic search with relevance ranking |
| Content extraction | None | Firecrawl: full page scrape, structured data |
| LLM-powered analysis | N/A | Firecrawl: `firecrawl_scrape` with LLM extraction |
| Batch operations | No | Firecrawl: `firecrawl_batch_scrape` |
| API key required | No (free) | Yes (Exa + Firecrawl keys) |

## Prerequisites

1. `mcp` Python SDK installed:
   ```bash
   pip install mcp
   ```

2. API keys:
   - **Exa**: sign up at https://exa.ai, get key from dashboard
   - **Firecrawl**: sign up at https://firecrawl.dev, get key from dashboard

## Configuration

Add to `~/.hermes/config.yaml` under `mcp_servers` (top-level key, not nested):

```yaml
mcp_servers:
  exa:
    command: "npx"
    args: ["-y", "exa-mcp-server"]
    env:
      EXA_API_KEY: "your-exa-api-key"
    timeout: 120
  firecrawl:
    command: "npx"
    args: ["-y", "firecrawl-mcp"]
    env:
      FIRECRAWL_API_KEY: "fc-your-firecrawl-key"
    timeout: 180
```

## Tools Provided After Gateway Restart

### Exa (`mcp_exa_*`)
- `mcp_exa_web_search_exa` — semantic web search with configurable result count
- `mcp_exa_get_code_context_exa` — find code examples and documentation
- `mcp_exa_web_search_exa_2` — alternative search with different parameters

### Firecrawl (`mcp_firecrawl_*`)
- `mcp_firecrawl_firecrawl_scrape` — scrape and extract content from a URL (markdown, structured data, LLM extraction)
- `mcp_firecrawl_firecrawl_search` — web search via Firecrawl
- `mcp_firecrawl_firecrawl_map` — discover URLs on a website
- `mcp_firecrawl_firecrawl_batch_scrape` — scrape multiple URLs at once
- `mcp_firecrawl_firecrawl_check_batch_status` — check batch job status

## Where to Use vs Legacy DuckDuckGo

- **Use Exa/Firecrawl MCP** for: research tasks, competitive intel, market data, documentation lookup, content extraction, anything needing high-quality results
- **Legacy DuckDuckGo** (`web_search` tool) still works as a free fallback when no API keys are configured

## Pitfalls

- **`mcp_servers` must be a top-level YAML key**, not nested under any section. Adding it inside `agent:` or `web:` silently fails.
- **Gateway restart required** after adding `mcp_servers`. MCP tools are discovered at startup only — no hot-reload.
- **First tool call after restart may be slow** (npx downloads the server package on first use if not cached). Subsequent calls are fast.
- **npm packages used**: `exa-mcp-server` and `firecrawl-mcp` (not `@anthropic/mcp-server-exa` — that package doesn't exist on npm). Both are published on the public npm registry.
- **`pip install mcp` is mandatory** — without it, MCP support is silently disabled at startup with "MCP SDK not available — skipping MCP tool discovery" in the gateway log.
- **Exa key format**: standard UUID-style string. **Firecrawl key format**: starts with `fc-` prefix.
- **do NOT add the keys to `.env`** — they go directly in `config.yaml` under `env:` for each MCP server, since MCP servers don't inherit the shell environment (Hermes filters env vars for security).
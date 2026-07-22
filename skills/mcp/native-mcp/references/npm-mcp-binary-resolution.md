# NPM MCP Binary Resolution — Diagnostic Playbook

## When an MCP server fails with "Connection closed" immediately

The most common cause: the Hermes gateway process cannot find or execute the MCP server binary. This happens frequently with Node.js MCP servers because the gateway's inherited `PATH` differs from your interactive shell.

## Step-by-Step Diagnosis

### 1. Find the right npm package name

```bash
npm search mcp-server-<name>    # search by keyword
npm search <name>-mcp           # alternate naming pattern
```

Example: `npm search mcp-server-exa` returns `exa-mcp-server` (the actual package name), not `@anthropic/mcp-server-exa` (which doesn't exist).

### 2. Install globally

```bash
npm install -g <package-name>
```

After install, the package lives at `$(npm root -g)/<package-name>/`.

### 3. Verify binary exists

```bash
ls $(npm root -g)/<package-name>/dist/       # dist/ is common
which <expected-binary-name>                  # may return path or nothing
ls ~/.hermes/node/bin/<binary-name>           # hermes-bundled node bin dir
```

### 4. Find the actual entry point (when bin symlink fails)

Not all npm packages symlink their binary reliably to the global bin directory. Use this to find the real entry:

```bash
cat $(npm root -g)/<package-name>/package.json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('bin:', d.get('bin','NONE')); print('main:', d.get('main','NONE'))"
```

Example output for `firecrawl-mcp`:
```
bin: {'firecrawl-mcp': 'dist/index.js'}
main: NONE
```

The entry point is `dist/index.js` relative to the package root.

### 5. Test the server directly

```bash
# With API key set
API_KEY="fc-..." $(npm root -g)/firecrawl-mcp/dist/index.js

# Or if the bin IS symlinked:
API_KEY="fc-..." firecrawl-mcp
```

It should start, print an MCP handshake, and wait for input. If it exits immediately with no output, the API key is missing or wrong.

### 6. Set config.yaml with absolute path

```yaml
mcp_servers:
  <name>:
    command: "/home/tapway/.hermes/node/bin/<binary-name>"   # if symlinked
    args: []                                                  # empty if using direct binary
    env:
      API_KEY: "fc-..."
    timeout: 180
```

**Alternative — if bin isn't symlinked:**
```yaml
mcp_servers:
  <name>:
    command: "/home/tapway/.hermes/node/bin/node"
    args: ["/home/tapway/.hermes/node/lib/node_modules/<package>/dist/index.js"]
    env:
      API_KEY: "fc-..."
    timeout: 180
```

### 7. Check gateway logs after restart

```bash
grep -i 'mcp.*discover\|mcp.*error\|mcp.*fail\|<server-name>' ~/.hermes/logs/errors.log | tail -20
grep -i 'mcp.*discover\|mcp.*error\|mcp.*fail\|<server-name>' ~/.hermes/logs/agent.log | tail -20
```

Look for:
- `unhandled errors in a TaskGroup (1 sub-exception)` → binary crashed immediately
- `Connection closed` → binary started but aborted before handshake
- No mention at all → config may have wrong server name or `command` path

## Confirmed Working Config Pattern

```yaml
mcp_servers:
  exa:
    command: "npx"
    args: ["-y", "exa-mcp-server"]
    env:
      EXA_API_KEY: "..."
    timeout: 120
  firecrawl:
    command: "/home/tapway/.hermes/node/bin/firecrawl-mcp"
    args: []
    env:
      FIRECRAWL_API_KEY: "fc-..."
    timeout: 180
```

**Key insight:** `exa-mcp-server` works with `npx -y` because it resolves correctly from npm. `firecrawl-mcp` needs a global install + absolute path because the bin symlink doesn't always work — and when it fails, `npx -y firecrawl-mcp` also fails because npx can't find the installed package's bin either.
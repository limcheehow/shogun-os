# {{VENDOR}} — {{DOMAIN_TITLE}} provider

## Credentials

| Env var | Required | Notes |
|---------|----------|-------|
| `{{PROVIDER_ENV}}` | yes | Set to `{{VENDOR_SLUG}}` |
| `{{API_KEY_ENV}}` | yes | From vendor console |

## MCP snippet (profile config.yaml)

```yaml
mcp_servers:
  {{MCP_SERVER_NAME}}:
    command: python3
    args: ["{{BRIDGE_PATH}}"]
    env:
      {{PROVIDER_ENV}}: "${{PROVIDER_ENV}}"
      {{API_KEY_ENV}}: "${{API_KEY_ENV}}"
```

## Profile .env

```bash
{{PROVIDER_ENV}}={{VENDOR_SLUG}}
{{API_KEY_ENV}}=...
```

## Verify

```bash
hermes -p {{PROFILE}} --exec "list available {{PREFIX}}_ tools"
# or call bridge health if implemented
```

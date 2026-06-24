---
name: gbrain-postgres-migration
description: "Migration from PGLite to local Postgres 16 with pgvector on WSL"
---

# gbrain Postgres Migration

## Stack
- **PostgreSQL 16 + pgvector 0.6.0** (via apt: `postgresql-16 postgresql-16-pgvector`)
- **gbrain** (Postgres backend)
- **MCP HTTP server** on port 8779 via systemd user service

## Config
- Database: `gbrain` owned by user `gbrain`
- Connection: `postgresql://gbrain@127.0.0.1:5432/gbrain` (trust auth, no password needed)
- gbrain config at `~/.gbrain/config.json`

## Key files
- Systemd service: `~/.config/systemd/user/gbrain-mcp.service`
- MCP server script: `~/.local/bin/gbrain-mcp.sh`
- MCP token: `~/.hermes/secrets/gbrain-mcp-token`
- Port registry: `~/.hermes/port-registry.json`
- Dream cycle cron: Hermes cron job (runs daily at 2 AM)

## MCP Server
```bash
# Start/stop/status
systemctl --user start gbrain-mcp.service
systemctl --user stop gbrain-mcp.service
systemctl --user status gbrain-mcp.service

# Health check
curl http://127.0.0.1:8779/health
```

## Dream Cycle
```bash
cd /home/cheehow/gbrain && /home/cheehow/.hermes/scripts/gbrain-runner.py dream --json
```

## Migration notes
- 27,471 pages migrated from PGLite → Postgres
- All 85 schema migrations applied (version 92)
- 100% embedding coverage
- No more PGLite lock contention issues
- Original PGLite brain backed up at `~/.gbrain.pglite-backup-20260609.tar.gz` (2.4G)
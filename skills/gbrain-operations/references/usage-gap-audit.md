# GBrain Usage Gap Audit (Jun 2026)

Session-specific audit of what's running vs available in gbrain v0.40.8.1 for CH's setup.
Generated from conversation on 2026-06-09. Updated 2026-06-09 after `gbrain extract all`.

## Methodology

```bash
# 1. Doctor health check
cd ~/gbrain && bun run src/cli.ts doctor

# 2. Integration status
cd ~/gbrain && bun run src/cli.ts integrations list

# 3. Source status
cd ~/gbrain && bun run src/cli.ts sources list

# 4. Verify autopilot
systemctl --user status gbrain-autopilot.service
tail -5 ~/.gbrain/autopilot.log

# 5. Check quartz config for encryption
grep -A5 "encrypted-pages" ~/brain-quartz/quartz.config.yaml

# 6. Port registry for running services
cat ~/brain/ops/port-registry.md

# 7. Brain site deployment docs
cat ~/brain/projects/brain-site/deployment.md
```

## Audit Result (Jun 2026)

### Running (✅)
- GBrain engine v0.40.8.1 — PGLite, 27,471 pages
- **Entity link graph** — 1,720 links across 20,583 pages (2% coverage) ✅
- **Timeline extraction** — 381 entries across 20,583 pages (1% coverage) ✅
- Brain score: **40/100** (was 37; embed 27/35, links 2/25, timeline 0/15, orphans 1/15, dead-links 10/10)
- `models.think` configured — `openrouter:anthropic/claude-sonnet-4` ✅
- `models.default` configured — `openrouter:anthropic/claude-sonnet-4` ✅
- Autopilot — systemd user service, inline PGLite mode (12s cycle, 150s gap)
- Quartz brain site — `cheehow-brain.gotapway.com` behind Cloudflare tunnel
- Auth proxy — HTTP Basic Auth, port 8766 → 8767
- Static server — Python HTTP on 8767 serving `~/brain-quartz/public/`
- Supabase REST sync — every 15 min via Python script, 20K+ files
- Brain query script → `~/.hermes/scripts/brain-query.sh`
- Brain capture script → `~/.hermes/scripts/brain-capture.sh`
- Brain think script → `~/.hermes/scripts/brain-think.sh`
- 14 Hermes cron jobs

### Not Running (❌ / 🔴 / ⚠️)

| Feature | Severity | Fix |
|---------|----------|-----|
| Embeddings: 77% coverage (6,720 missing) | ⚠️ | `gbrain embed --stale` (pause autopilot first) |
| Brain score still low on links/timeline (2%/1%) | ⚠️ | Rerun `gbrain extract all` after adding more `[[wikilinks]]` and frontmatter dates |
| Git pre-commit hook | ❌ | `gbrain frontmatter install-hook` |
| gbrain MCP server | ❌ | `gbrain serve` (contends with autopilot on PGLite) |
| Dream cycle (synthesize/patterns/consolidate) | ❌ | Config `dream.synthesize.enabled true` + transcript corpus |
| Quartz encrypted-pages | ❌ | `gbrain publish` standalone only |
| Schema packs | ❌ | No custom page types |
| Takes / hunches | ❌ | No knowledge claims created |
| Email-to-brain | ❌ | Needs credential-gateway |
| Calendar-to-brain | ❌ | Needs credential-gateway |
| X-to-brain | ❌ | Twitter API keys |
| Meeting-sync | ❌ | Circleback webhook |
| Integrations (all 6) | ❌ | All `AVAILABLE` via `gbrain integrations list` |
| Minions / subagents | ❌ | Requires Postgres (PGLite lock prevents) |

### What the User Has That Works Well
- 27K pages beautifully organized in `~/brain/` with semantic folders
- Quartz site looks professional (dark theme, search, explorer, graph view)
- Autopilot keeps content synced continuously (12s cycle, ~50% score maintained)
- Supabase REST sync runs every 15 min for zero-contention reads
- **gbrain think** now works with proper model config — multi-hop synthesis across 27K pages
- 3 utility scripts for integration: query (Supabase REST), capture (filesystem), think (pause/resume autopilot)
- 14 cron jobs for trading alerts, market briefings, etc.

### Quick Wins (Least Effort → Most Impact)
1. `gbrain embed --stale` (pause autopilot first) — get embeddings 77% → 100%, brain score jumps ~30pts
2. `gbrain frontmatter install-hook` — prevent YAML errors before commit
3. Enable `encrypted-pages` Quartz plugin for password-gated pages on the live site
4. `gbrain features` — browse other unused features
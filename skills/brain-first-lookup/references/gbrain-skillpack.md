# gbrain Skillpack Reference

The gbrain repo at `github.com/garrytan/gbrain` ships a `/skills/` directory (default branch: `master`) with ~47 skills. These are **not Hermes agent skills** — they are the canonical workflow descriptions for gbrain itself, authored by Garry Tan.

## Structure

```
skills/
  _AGENT_README.md          ← routing contract: how to discover skills at runtime
  _brain-filing-rules.md    ← where to file brain pages (read on every write)
  _output-rules.md          ← output quality standards
  _friction-protocol.md     ← log user friction to ~/.gstack/friction/
  manifest.json             ← v0.32.3.0, 47 skills declared
  conventions/              ← cross-cutting rules every skill defers to
  <skill-name>/SKILL.md     ← the skill's workflow + YAML frontmatter with triggers
  RESOLVER.md               ← retired routing table (replaced by trigger-based dispatch)
```

## How to use them

1. **Browse** the manifest at `github.com/garrytan/gbrain/skills/manifest.json` to see what exists
2. **Read** a specific skill via `curl -s https://raw.githubusercontent.com/garrytan/gbrain/master/skills/<slug>/SKILL.md`
3. **Invoke** by matching user intent against the skill's `triggers:` in YAML frontmatter

Each skill declares triggers in its YAML frontmatter — the agent matches user phrases against those at runtime.

## Skill Categories

### Core read/write
| Skill | Triggers / When to use |
|-------|----------------------|
| **capture** | Single-verb entry point: "capture this thought", "save this idea" |
| **ingest** | "ingest this URL", "import this file" — routes content to the right pipeline |
| **query** | "answer this question", "what does the brain know about X" — 3-layer search+synth |
| **brain-ops** | Core read-enrich-write loop, brain-first lookup, source attribution |
| **enrich** | Tiered enrichment for person/company pages |
| **maintain** | "check brain health", "fix broken links", "find orphans" |
| **frontmatter-guard** | Validates YAML frontmatter on every write — gates malformed YAML, null bytes |

### Content acquisition
| Skill | When to use |
|-------|-------------|
| **idea-ingest** | Links, articles, tweets with entity cross-linking |
| **media-ingest** | Video, audio, PDF, book, screenshots with entity extraction |
| **meeting-ingestion** | Meeting transcripts with attendee enrichment |
| **voice-note-ingest** | Voice notes — exact phrasing preserved (never paraphrased) |
| **book-mirror** | "mirror this book", "two-column book analysis" — personalized chapter-by-chapter |
| **archive-crawler** | Personal file archives (Dropbox, B2, email exports) — high-value content only |
| **data-research** | Structured parameterized research: investor updates, company metrics |

### Analysis & synthesis
| Skill | When to use |
|-------|-------------|
| **briefing** | "daily briefing", "what happened today" |
| **concept-synthesis** | Deduplicate concept stubs into T1→T4 tiered intellectual map |
| **idea-lineage** | "trace this idea", "find contradictions" — evolution through the brain |
| **strategic-reading** | "read this through the lens of problem X" — produces applied playbook |
| **perplexity-research** | "research this topic" — surfaces what's NEW vs already-known in brain |
| **academic-verify** | Verify academic citations against current literature |

### Infrastructure
| Skill | When to use |
|-------|-------------|
| **setup** | Bootstrap gbrain: auto-provision Supabase/PGLite |
| **migrate** | Import from Obsidian, Notion, Logseq, Roam, CSV |
| **cold-start** | Day-one brain bootstrapping — highest-leverage data sources first |
| **publish** | "share this page" — password-protected HTML |
| **minion-orchestrator** | Submit/monitor/steer background jobs |
| **cron-scheduler** | Schedule management with quiet hours + wake-up override |
| **smoke-test** | Post-restart health checks + auto-fix |
| **gbrain-upgrade** | "upgrade gbrain" — keep current |
| **skillpack-check** | Agent-readable health report (cron-friendly) |

### Governance & quality
| Skill | When to use |
|-------|-------------|
| **soul-audit** | 6-phase interview generating SOUL.md, USER.md, ACCESS_POLICY.md, HEARTBEAT.md |
| **brain-taxonomist** | Filing gate: "where should I put this" — reads schema pack, recommends path |
| **testing** | "test this skill" — frontmatter, MECE checks, manifest coverage |
| **eiirp** | "organize everything" — 7-phase post-work organizer (Everything In Its Right Place) |
| **schema-author** | "add a new page type" — evolve active schema pack |
| **schema-unify** | "unify schema types" — migrate noisy pack to 15 canonical types |
| **skillify** | "turn this into a skill" — meta skill + gbrain check-resolvable |
| **skill-optimizer** | SkillOpt-paper-grounded text-space optimizer, validation gating, atomic writes |
| **skillpack-harvest** | "lift this skill into gbrain" — genericization checklist for upstream contribution |

## How this differs from Hermes skills

| Dimension | Hermes skills (here) | gbrain skills (the repo) |
|-----------|---------------------|--------------------------|
| Location | `~/.hermes/skills/` | `github.com/garrytan/gbrain/skills/` |
| Loaded via | `skill_view(name)` | `curl $(skill's raw URL)` or `gbrain skillpack scaffold <slug>` |
| Purpose | Agent-interface conventions for this user's setup | Canonical gbrain workflows authored by Garry Tan |
| Discovery | Via `skills_list` in Hermes tool | Via `manifest.json` + YAML frontmatter triggers |
| Ownership | Local agent-created or curated by user | Shipped with gbrain, updated via `gbrain upgrade` |

When a new gbrain version ships, run `gbrain skillpack reference --all` to see which local scaffolded skills differ from the bundle.

## Hermes gbrain Skills (this agent)

These are Hermes agent skills (in `~/.hermes/skills/gbrain/`) that adapt the canonical gbrain repo workflows for this user's setup. Load them via `skill_view(name)` — they drive the actual MCP tool calls.

| Hermes skill | Maps to gbrain repo skill | What it does |
|--------------|--------------------------|--------------|
| `gbrain-query` | `query` | Three-layer pipeline: search → recall → think. Escalation ladder for all brain queries |
| `gbrain-ingest` | `ingest` | Import URLs, files, docs → extract entities → file correctly → cross-link |
| `gbrain-capture` | `capture` | Quick capture of ideas/thoughts with exact phrasing preservation |
| `gbrain-brain-ops` | `brain-ops` | Read-enrich-write loop, sync, health dashboard, source management |
| `gbrain-enrich` | `enrich` | Tiered enrichment (1/2/3) for person/company/project pages |
| `gbrain-maintain` | `maintain` | Health checks, orphan fixing, staleness review, contradiction detection |
| `gbrain-frontmatter-guard` | `frontmatter-guard` | Pre-write YAML validation: malformed YAML, null bytes, missing fields |
| `gbrain-idea-ingest` | `idea-ingest` | Link/article/tweet ingestion with entity cross-linking |
| `gbrain-media-ingest` | `media-ingest` | Video/audio/PDF/screenshot ingestion with transcript/OCR extraction |

### Existing Hermes gbrain skills (before this set)

| Hermes skill | Maps to | Purpose |
|-------------|---------|---------|
| `brain-first-lookup` | `query` + `brain-ops` | Mandatory protocol: query brain before external APIs |
| `gbrain-think` | `query` (think layer) | Multi-hop synthesis with citation + gap analysis |
| `gbrain-signal-detector` | `capture` | Ambient signal capture for ideas and entities in conversation |

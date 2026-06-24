# GBrain Publish, Report & Capture Reference

Session-specific detail on using gbrain's v0.38+ capture/report and v0.29+ publish features.

## Publish — Share Brain Pages as HTML

### How to invoke
```bash
cd ~/gbrain && gbrain publish <path-to-brain-page> [options]
```

### Required options
| Option | Purpose | Example |
|--------|---------|---------|
| `<path>` | Path to the .md file to publish | `~/brain/companies/acme.md` |
| `--out <path>` | Output HTML file path | `--out /tmp/share.html` |

### Security options
| Option | Default | Description |
|--------|---------|-------------|
| No `--password` | Auto-generates one | Prints password to stdout; save+share it |
| `--password <val>` | — | Set your own password or use a previously generated one |
| `--password` (bare) | Same as auto-generated | Flags that encryption IS wanted |

### What gets stripped
- YAML frontmatter
- `[Source:]` citation footnotes
- Confirmation numbers and internal IDs
- `[[wikilinks]]` (converted to plain text)
- Timeline sections
- Private notes (`private:` / `_private:` markers)

### Best use cases for CH
- Share a company profile with a potential partner
- Export a trip itinerary for family
- Send a deal summary to a client
- Create a one-page brief from a longer analysis

### Batch publish example
```bash
for f in ~/brain/meetings/2026/05/*.md; do
  gbrain publish "$f" --out "/tmp/share/$(basename "$f" .md).html"
done
```

## Report — Timestamped Reports

### How to invoke
```bash
cd ~/gbrain && gbrain report --type <name> --content "<text>" [--slug <slug>]
```

### Options
| Option | Purpose | Example |
|--------|---------|---------|
| `--type` | Short label for the report category | `weekly-review`, `trip-debrief`, `post-mortem` |
| `--content` | Report body text | `"Trip to Japan: visited 3 cities..."` |
| `--slug` | Custom path within `brain/reports/` | `weeklies/2026-05-24` |

### When to use report vs regular page
| | report | Regular page |
|---|---|---|
| Time-bound | ✅ Yes — timestamped | ❌ Not automatically |
| Metadata-rich | ✅ type + slug + date frontmatter | Manual YAML |
| Best for | Weekly reviews, trip debriefs, decision records, RCAs | Company profiles, person bios, concept notes, ideas |

## Capture — Unified Entrypoint

### How to invoke
```bash
cd ~/gbrain && gbrain capture "<content>" [--type <type>] [--slug <slug>]
```

### Type routing
| Type | Destination | When to use |
|------|-------------|-------------|
| `idea` | `brain/ideas/` | Your own product/business sparks |
| `concept` | `brain/concepts/` | Frameworks others coined (e.g., Jevons Paradox) |
| `wiki` | `brain/wiki/` | Evergreen reference knowledge |
| (no type) | `brain/inbox/` | Uncategorized — needs routing later |
| `--file <path>` | Per `--slug` or inbox | Capture content from a file instead of inline text |

### Capture from email (workflow)
```bash
# Read email → capture to brain
himalaya envelope read <id>
gbrain capture "Interesting insight from email: X is partnering with Y on Smart City" --type concept
```

### Capture from web research
```bash
# Found something worth saving
gbrain capture "Jevons Paradox: when efficiency increases usage instead of decreasing it — relevant to Tapway's energy-efficient cameras lowering adoption barrier" --type concept --slug concepts/jevons-paradox-tapway
```

## Interaction Notes

### CH's preferred workflow
1. **Ideas** → `--type idea` for raw sparks ("What if we built X?")
2. **People/companies from email** → structured person/company pages (Himalaya → write_file → gbrain sync)
3. **Publish** → only when explicitly asked ("Send me that page as HTML")
4. **Report** → weekly summaries or post-trip debriefs

### Gotchas
- `gbrain publish` generates a **self-contained HTML** — no server needed. Just share the file.
- `gbrain capture` writes to `brain/inbox/` by default — remember to route interesting items to the right folder.
- `gbrain report` writes to `brain/reports/` with date + type — the cron-to-brain pattern in `brain-folder-organization` handles daily writes.
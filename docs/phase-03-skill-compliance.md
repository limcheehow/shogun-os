# Phase 3: Skill Compliance

**Version:** 2.1.0  
**Date:** 2026-06-22  
**Status:** ✅ Complete

## Goal

Make all skills in the repo compliant with Hermes skill conventions: proper frontmatter, `triggers` metadata, and CLI-installable structure.

## Changes

### `skills/brain-ingest-pipeline/SKILL.md`

Added `metadata.hermes.triggers` section to define when the skill should auto-load:

```yaml
metadata:
  hermes:
    triggers: [email, calendar, brain, ingest, triage, pipeline]
    tags: [...]
```

### What Makes a Hermes-Compliant Skill

| Requirement | Description | Verified |
|-------------|-------------|----------|
| YAML frontmatter | `---\nname: ..., description: ..., version: ..., author: ...\n---` | ✅ |
| `metadata.hermes.triggers` | Array of keywords that auto-load the skill when mentioned | ✅ |
| `metadata.hermes.tags` | Search/filter tags | ✅ |
| Clear heading structure | Standard markdown with progressive detail | ✅ |
| Self-contained | All references/templates/scripts linked within the skill directory | ✅ |

### Verification

```bash
# Validate frontmatter
python3 -c "
import yaml, sys
for f in ['skills/brain-ingest-pipeline/SKILL.md', 'skills/department-scrum/SKILL.md']:
    with open(f) as fh:
        lines = fh.read().split('---')
        meta = yaml.safe_load(lines[1])
        assert meta.get('name'), f'{f}: missing name'
        assert meta.get('metadata', {}).get('hermes', {}).get('triggers'), f'{f}: missing triggers'
        print(f'✅ {f} — compliant')
"
```
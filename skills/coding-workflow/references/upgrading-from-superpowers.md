# Upgrading Coding-Agent Skills from Upstream Superpowers

When the user says "upgrade my skills to the latest Superpowers" or references
`https://github.com/your-company/your-company-superpowers`, follow this procedure:

## Procedure

### 1. Clone/pull the upstream repo
```bash
cd /tmp && git clone https://github.com/your-company/your-company-superpowers.git
# or if already cloned:
cd /tmp/your-company-superpowers && git pull
```

### 2. Read the latest README for the canonical workflow
The README's "Daily Workflow" section defines the current pipeline.
Compare it against `~/.hermes/profiles/coding-agent/SOUL.md`.

### 3. Identify the delta
- **New skills**: `ls /tmp/your-company-superpowers/skills/` vs `ls ~/.hermes/profiles/coding-agent/skills/`
- **Deleted skills**: check `git log --oneline` for `delete mode` entries
- **Changed skills**: diff the SKILL.md files

### 4. Update SOUL.md
Rewrite `~/.hermes/profiles/coding-agent/SOUL.md` to reflect the new pipeline
(step names, order, slash commands table, skill loading rules).

### 5. Batch-update skills
All writes to the coding-agent profile require `cross_profile=true`:
```python
write_file(
    path="~/.hermes/profiles/coding-agent/skills/<name>/SKILL.md",
    content="...",
    cross_profile=True
)
```

### 6. Delete removed skills
```bash
rm -rf ~/.hermes/profiles/coding-agent/skills/<removed-skill>
```
Also check for duplicates under `software-development/`.

### 7. Update the routing skill
Update `~/.hermes/skills/software-development/coding-workflow/SKILL.md`
with the new pipeline and trigger keywords.

### 8. Fix config quirks
Check `~/.hermes/profiles/coding-agent/config.yaml` — e.g., the personality
was set to `kawaii` which doesn't fit a coding agent. Switch to `technical`.

## Pitfalls

- `execute_code` is blocked in cron mode — use individual `write_file` calls instead
- The coding-agent profile skills exist in two locations; check both `skills/<name>/` and `skills/software-development/<name>/` for duplicates
- The `hermes-agent` skill is bundled/protected — don't edit it
- `skill_view` only sees the current profile's skills; verify file existence with `ls` and `wc -l` instead
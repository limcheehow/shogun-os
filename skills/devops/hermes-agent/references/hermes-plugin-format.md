# Hermes Plugin Format — Cross-Platform Reference

Claude Code (Anthropic) uses `.plugin` files — binary/archive bundles containing plugin metadata, JavaScript/Python code, and configuration. They are specific to Claude's runtime.

**Hermes does not support `.plugin` files.**

## Hermes Plugin Format

Hermes plugins are **Python module directories** under `~/.hermes/hermes-agent/plugins/`:

```
plugins/<name>/
├── __init__.py       # Plugin registration, tool definitions, hooks
├── ...               # Supporting Python modules
└── SKILL.md          # Optional: skill docs that load with the plugin
```

Each plugin is a standard Python package. No binary archives, no special bundle format.

## CLI

```
hermes plugins list                  # Show all plugins (bundled + user)
hermes plugins enable <name>         # Enable a plugin
hermes plugins disable <name>        # Disable a plugin
```

## To Port a Claude Plugin to Hermes

1. Extract the Claude plugin's source code (`.plugin` files are zip archives — `unzip` may work)
2. Understand what tools/hooks the plugin provides
3. Recreate it as a Hermes plugin directory with `__init__.py` following the plugin API
4. Register tools via the tool registry pattern

## Alternative: Skills Instead of Plugins

Many plugin-like capabilities can be implemented as a **SKILL.md** instead — no Python module required. Skills are just markdown with instructions, references, templates, and optional scripts. This is the Hermes-native way to add capabilities without writing a full plugin.

Use a plugin when you need:
- Low-level tool registration with custom Python logic
- Lifecycle hooks (startup/shutdown)
- Integration with Hermes internal APIs

Use a skill when you need:
- Workflow guidance and reusable procedures
- Reference data, templates, and scripts
- Tool-calling patterns without custom code

## Converting a Claude Workflow/Skill Plugin to Hermes Skills

This is the most common migration path — Claude `.plugin` files from marketplaces or coworker repos that contain **skill/workflow definitions** (not Python code). Each Claude "skill" in the plugin becomes a Hermes SKILL.md.

### Step 1 — Identify the Plugin Type

Extract the `.plugin` (it's a renamed zip or tar.gz):

```bash
file some-plugin.plugin       # check if it's Zip or gzip compressed
mv some-plugin.plugin some-plugin.zip && unzip some-plugin.zip -d ./plugin-extracted/
```

Check the layout:
- **Skill/workflow plugin** — directories named by feature, each with `.md` files + possibly JSON configs. No `__init__.py`. This is the common case.
- **Code plugin** — contains `.js`/`.py` files, a `manifest.json` with tool definitions. Maps to Hermes's `plugins/` Python module format.

### Step 2 — Extract Skill Definitions

For each skill directory in the extracted plugin, read the Claude skill file to understand:

1. **Trigger patterns** — What user prompts activate this skill?
2. **Tool calls** — What Claude-specific tools does it use?
3. **Expected output format** — What does it produce?
4. **File paths** — Where does it read/write?

### Step 3 — Map Claude Tools to Hermes Equivalents

| Claude Tool | Hermes Equivalent | Notes |
|---|---|---|
| `slack_send_message()` | `send_message()` | Hermes auto-resolves target; pass platform:channel format |
| `read_file()` | `read_file()` | Same API (path, offset, limit) |
| `write_file()` | `write_file()` | Always overwrites; use `patch()` for edits |
| `edit_file()` | `patch()` | Find-and-replace with fuzzy matching |
| `grep()` / `search_files()` | `search_files()` | Regex content search + file name search |
| `execute_command()` | `terminal()` | Foreground + background modes |
| Claude-specific MCP tools | Native MCP / inline | Configure server in `config.yaml` |
| `list_files()` | `search_files(target='files')` | Use with glob patterns |

### Step 4 — Convert Each Skill

For each Claude skill definition, create a Hermes SKILL.md:

```yaml
---
name: my-skill
description: >-
  Short one-line description of what this skill does.
tags: [category, subcategory, relevant-tags]
---
```

**Key adaptations:**

1. **Add YAML frontmatter** — Claude plugins use different metadata formats. Always write Hermes-standard frontmatter with `name`, `description`, `tags`.

2. **Tool call conversion** — Replace every Claude-specific tool call with its Hermes equivalent (table above). Pay attention to keyword arguments.

3. **Path adaptation** — Convert Windows paths (`C:\Users\...`) to Hermes environment paths:
   - `/mnt/c/Users/...` for WSL access to Windows files
   - `~/brain/` for gbrain markdown repository
   - `~/brain/projects/` for project management files

4. **Trigger patterns** — Keep Claude-style "When user says X" sections. Format as tables:
   ```
   | User says | Action |
   |---|---|
   | "create project" | Run ONBOARD MODE |
   ```

5. **Remove Claude-specific framing** — Strip "You are a Claude agent" instructions. Persona belongs in `SOUL.md`, not individual skills.

### Step 5 — Write Skills to the Target Profile

```
~/.hermes/profiles/<profile-name>/skills/<category>/<skill-name>/SKILL.md
```

### Step 6 — Wire into the Profile's SOUL.md

Add skills under "Always Load Before Working" and key paths to the profile's SOUL.md.

### Pitfalls

- **Claude `.plugin` files may not unzip directly** — try `tar -xzf` if `unzip` fails.
- **Some Claude skills reference `@persona` or agent context** — no Hermes equivalent. Strip or rephrase.
- **Profile skills directory may not exist** — `write_file` creates parent dirs automatically.
- **SOUL.md edits take effect immediately** — no gateway restart needed.
- **Gateway restart IS needed** for `channel_prompts` or `config.yaml` changes.
- **`unzip` may not be installed** — `sudo apt install unzip` or use Python's `zipfile`.
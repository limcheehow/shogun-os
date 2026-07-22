# Authoring Shareable Agent Frameworks

Package a Hermes agent as a **distributable product** for other businesses, teams, or community users. Combines profile distributions (agent shell), structured brain repos (knowledge base), and plugins (custom tools/hooks) into a complete framework — the pattern the Company gbrain exemplifies.

## The Three-Layer Architecture

```
my-framework/
│
├── profile-distribution/        ← Layer 1: Agent Shell
│   ├── distribution.yaml        Manifest (name, version, env requirements)
│   ├── SOUL.md                  Agent personality
│   ├── config.yaml              Model, provider, tools defaults
│   ├── skills/                  Bundled skills (workflows, domain knowledge)
│   ├── cron/                    Scheduled tasks (data syncs, reports)
│   └── mcp.json                 MCP server connections
│
├── brain-repo/                  ← Layer 2: Knowledge Base (companion git repo)
│   ├── SOUL.md                  Brain identity that agents read at startup
│   ├── ACCESS_POLICY.md         Who can read/write what
│   ├── RESOLVER.md              Placement rules for new pages
│   ├── HEARTBEAT.md             Operational cadence
│   ├── people/                  Per-person profiles
│   ├── projects/                Project records
│   ├── companies/               Org profiles
│   ├── concepts/                Framework/pattern notes
│   ├── meetings/                Meeting minutes
│   └── data/                    Structured data dumps (collected via cron)
│
└── plugins/                     ← Layer 3: Custom Extensions
    └── my-integration/
        ├── plugin.yaml          Metadata + hook/tool declarations
        ├── __init__.py          register(ctx) function
        └── requirements.txt
```

## Layer 1: The Agent Shell (Profile Distribution)

The profile distribution is the **primary delivery vehicle**. It makes your agent installable, versionable, and updatable.

### Manifest (`distribution.yaml`)

```yaml
name: my-framework
version: 1.0.0
description: "Business assistant framework — structured AI for [domain]"
hermes_requires: ">=0.12.0"
author: "Your Company"
license: "Commercial"
env_requires:
  - name: OPENAI_API_KEY
    description: "OpenAI API key for model access"
    required: true
  - name: BRAIN_PATH
    description: "Path to the business brain repo"
    required: false
    default: "~/brain"

distribution_owned:   # What gets replaced on update
  - SOUL.md
  - config.yaml
  - skills/
  - cron/
  - mcp.json
```

### Installation flow

```bash
# User installs your framework
hermes profile install github.com/your-org/my-framework --alias

# Fill in API keys
cp ~/.hermes/profiles/my-framework/.env.EXAMPLE ~/.hermes/profiles/my-framework/.env

# Clone the companion brain repo
cd ~ && git clone git@github.com:client/brain.git brain

# Done — run the agent
my-framework chat
```

On update (`hermes profile update my-framework`):
- **Distribution-owned files** (SOUL.md, skills/, cron/, mcp.json) are replaced
- **User-owned data** (memories, sessions, .env, auth.json) is **never touched**
- `config.yaml` is preserved by default (pass `--force-config` to reset)

### What goes in the distribution vs what doesn't

| Include | Don't Include |
|---------|---------------|
| SOUL.md, config.yaml | API keys (.env) |
| skills/, cron/, mcp.json | auth.json |
| distribution.yaml | memories/, sessions/ |
| README.md | state.db*, logs/ |

### Credential strategy

Every installer brings their own API keys. The `.env.EXAMPLE` shipped with the distribution documents exactly what's needed:

```
# OpenAI API key (required)
OPENAI_API_KEY=*** Brain repo path (optional, defaults to ~/brain)
BRAIN_PATH=~/brain
```

## Layer 2: The Knowledge Base (Structured Brain Repo)

The brain repo is a **separate git repository** that the agent reads/writes. Each business gets their own brain with their own people, projects, and data.

### Key files

| File | Purpose |
|------|---------|
| `SOUL.md` | Agent identity for this specific business (overlays profile SOUL) |
| `ACCESS_POLICY.md` | Permissions model — who can read/write which sections |
| `RESOLVER.md` | Decision tree for where to file new pages |
| `HEARTBEAT.md` | Operational cadence (daily briefings, review cycles) |

### Standard directories

```
people/          Individual person profiles (<slug>.md with frontmatter)
projects/        Active work efforts
companies/       Organizations, partners, vendors
concepts/        Patterns, frameworks, technologies
meetings/        Meeting notes and decisions
data/            Structured data from cron collectors (CSV, markdown)
inbox/           Catch-all for unclassified pages
sources/         External reference material
```

### Cron-driven data collection

Schedule regular scripts that pull from external APIs and write to `~/brain/data/`:

```python
# Example: collect-leave-summaries.py
# 1. Auth to BrioHR / BambooHR / your HR system
# 2. Fetch leave balances for all staff
# 3. Write to ~/brain/data/hr/leave-summaries/<date>.csv
# 4. Optionally update per-person markdown files in ~/brain/people/
```

Cron setup (no-agent mode = script output IS the message):

```bash
# Create wrapper script
cat > ~/.hermes/scripts/brain-sync.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/brain"
python3 $HOME/.hermes/scripts/collect-data.py
git add -A && git commit -m "daily sync $(date +%Y-%m-%d)" || true
git push
EOF

chmod +x ~/.hermes/scripts/brain-sync.sh

# Schedule daily at 8am
hermes cron create '0 8 * * *' --name 'Brain Sync' --script brain-sync.sh --no-agent --deliver local
```

## Layer 3: Custom Extensions (Plugins)

When profile assets aren't enough — you need custom Python code running in the agent's process.

### Plugin structure

```
plugins/my-plugin/
├── plugin.yaml          # Metadata + lifecycle hooks
├── __init__.py          # register(ctx) function
└── requirements.txt     # (optional) extra dependencies
```

### `plugin.yaml`

```yaml
name: my-plugin
version: 1.0.0
description: "Custom integration for [service]"
author: "Your Company"
hooks:
  - post_tool_call
  - on_session_end
```

### `__init__.py`

```python
import logging
logger = logging.getLogger(__name__)

def register(ctx):
    """Called by Hermes when the plugin loads."""
    # Register a custom tool
    ctx.register_tool(
        name="my_custom_action",
        toolset="custom",
        schema={...},
        handler=handle_custom_action,
        description="Does [X] via the [Y] API",
    )

    # Register a lifecycle hook
    ctx.register_hook("post_tool_call", on_tool_call)

    # Register a slash command for chat sessions
    ctx.register_command(
        "myaction",
        handler=handle_slash,
        description="Run [X] — usage: /myaction <arg>",
        args_hint="<arg>",
    )

    # Register a CLI command (hermes mycommand)
    ctx.register_cli_command(
        "mycommand",
        help="Manage [X] integration",
        setup_fn=setup_parser,
        handler_fn=handle_cli,
    )

def handle_custom_action(args, **kw):
    """Tool handler — must return JSON string."""
    import json
    param = args.get("param", "")
    return json.dumps({"result": param, "success": True})

def on_tool_call(tool_name="", args=None, result=None, **kw):
    """Lifecycle hook — fires after every tool call."""
    pass

def handle_slash(raw_args: str) -> str:
    """Slash command handler."""
    return f"Result: {raw_args}"

def setup_parser(subparser):
    subparser.add_argument("--flag", help="...")

def handle_cli(args):
    print(args.flag)
```

### Available hooks

| Hook | When it fires |
|------|---------------|
| `pre_tool_call` | Before a tool runs |
| `post_tool_call` | After a tool runs |
| `transform_terminal_output` | Modify terminal output before it reaches the model |
| `transform_llm_output` | Modify LLM response before sending to user |
| `pre_llm_call` | Before LLM API call |
| `post_llm_call` | After LLM API call |
| `pre_api_request` | Before HTTP request |
| `post_api_request` | After HTTP response |
| `on_session_start` | New session begins |
| `on_session_end` | Session ends |
| `subagent_start` | Subagent spawned |
| `subagent_stop` | Subagent finished |
| `pre_gateway_dispatch` | Gateway received message but before auth/dispatch |
| `pre_approval_request` | Dangerous command needs approval |
| `post_approval_response` | User responded to approval |

### Plugin source locations (later overrides earlier)

| Source | Path |
|--------|------|
| Bundled | `<hermes-repo>/plugins/<name>/` |
| User | `~/.hermes/plugins/<name>/` |
| Project | `./.hermes/plugins/<name>/` (opt-in) |
| Pip | `pip install hermes-agent-myplugin` |

Plugins are **opt-in by default** — must be listed in `config.yaml`:
```yaml
plugins:
  enabled:
    - my-plugin
```

## Delivery & Update Architecture

```
You (framework author)               Clients (businesses)
────────────────────────────         ────────────────────────────────
Profile distribution (git repo) ──▶  hermes profile install
  ├── distribution.yaml              Creates ~/.hermes/profiles/<name>/
  ├── SOUL.md                        Prompts for .env vars
  ├── skills/
  └── cron/
                                           │
Brain repo template ──▶               Client forks/clones own brain
  ├── SOUL.md                               │
  ├── ACCESS_POLICY.md                Maintains their own data
  ├── people/
  └── projects/

                                          ▼
                                   hermes profile update my-framework
                                   (pulls your latest agent changes,
                                    keeps their API keys + brain data)
```

### Version strategy

| Change | Action |
|--------|--------|
| Bug fix to SOUL or skill | Commit + push → clients update |
| New skill or cron job | Same |
| Breaking config change | Bump version in `distribution.yaml`, tag git, document migration |
| Per-client customization | They maintain their own `~/brain/` repo — your framework is the agent shell; their brain is their data |
| Plugin update | Re-copy `~/.hermes/plugins/` or publish via pip |

## Migration Path: Existing Setup → Distributable Framework

If you already have a working Hermes setup (like your company's gbrain), packaging it is:

```bash
# 1. Create the distribution manifest
cd ~/.hermes/profiles/default
cat > distribution.yaml << 'EOF'
name: company-framework
version: 1.0.0
description: "Company Business Framework"
hermes_requires: ">=0.12.0"
author: "Company Sdn Bhd"
env_requires:
  - name: OPENAI_API_KEY
    required: true
  - name: BRAIN_PATH
    default: "~/brain"
    required: false
EOF

# 2. Pick which parts go in the distribution
#    Copy your SOUL.md, config.yaml, skills/, cron/

# 3. Initialize git and push
git init
git add distribution.yaml SOUL.md config.yaml skills/ cron/
git commit -m "v1.0.0"
git remote add origin git@github.com:tapway/tapway-framework.git
git tag v1.0.0
git push -u origin main --tags

# 4. Test the install
hermes profile install github.com/tapway/tapway-framework --name test-install
```

### What the client brain setup looks like

```bash
# Each client runs:
hermes profile install github.com/tapway/tapway-framework --alias

# Fill in .env
# Then they clone or create their own brain:
mkdir -p ~/brain/{people,projects,companies,concepts,meetings,inbox,sources,data}
echo "# ACCESS_POLICY.md" > ~/brain/ACCESS_POLICY.md
echo "# RESOLVER.md" > ~/brain/RESOLVER.md
echo "# HEARTBEAT.md" > ~/brain/HEARTBEAT.md
git init ~/brain && cd ~/brain && git add -A && git commit -m "init"
```

### Private repo considerations

- Private git repos work transparently (SSH keys, GitHub CLI auth)
- The `.env.EXAMPLE` documents what API keys the client needs — they provide their own
- No secrets ever leave the client's machine
- The brain repo is separate from the profile distribution — each client owns their brain; you own the framework

## Design Decisions Summary

| Issue | Recommendation |
|-------|---------------|
| Framework versioning | Git tags on the profile distribution repo |
| Per-client data | Separate brain repo per client |
| Secret management | `.env.EXAMPLE` + client's own `.env` |
| API key rotation | Client edits their `.env`, no framework change needed |
| Cron jobs that survive updates | Bundle in the profile distribution; user data untouched |
| Custom business logic | Plugins (`~/.hermes/plugins/`) or skills |
| Multiple agent personas | One profile per business type, or channel prompts in one profile |
| Open source vs commercial | Same mechanism; `distribution.yaml` license field for attribution |
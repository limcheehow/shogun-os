---
name: profile-provisioning
category: ops
setup_time: 20 min
cost: $0
depends_on: [hermes-agent]
---

# Profile Provisioning

Create and manage Hermes profiles — SOUL.md authoring, config.yaml templates, systemd enable+start, and skill installation. Each profile is a separate persona with its own gateway, skills, tools, and cron jobs.

## Architecture

```
profiles/<name>/
  ├── SOUL.md          — Persona definition (identity, behavior, constraints)
  ├── config.yaml      — Profile-specific settings (model, tools, delivery)
  ├── scripts/         — Symlinks to shared scripts
  ├── skills/          — Profile-specific skills
  └── cron/            — Profile-specific cron jobs
```

## Setup

### Step 1: Create a profile directory

```bash
# Create the profile directory structure
mkdir -p ~/.hermes/profiles/<profile-name>/{scripts,skills,cron}

# Basic config.yaml
cat > ~/.hermes/profiles/<profile-name>/config.yaml << 'YAML'
profile:
  name: <profile-name>
  description: "Description of this profile's purpose"

model:
  default: your-model
  provider: custom
  base_url: https://your-provider.example.com/v1
  api_key: ${API_KEY_VAR}
  api_mode: chat_completions

gateway:
  port: 0  # auto-assign
  host: "127.0.0.1"

delivery:
  default: local
  fallback: local

tools:
  enabled:
    - terminal
    - file
    - search
    - web
YAML
```

### Step 2: Author the SOUL.md

The SOUL.md defines the profile's identity and behavioral constraints. Write to `~/.hermes/profiles/<profile-name>/SOUL.md`:

```markdown
# SOUL: <Profile Name>

## Identity
You are a [role description]. You handle [responsibilities].

## Behavioral Constraints
- Always check tool output before reporting success
- Prefer deterministic Python over fragile LLM chains
- Never fabricate data — report blockers honestly
- Use gbrain for knowledge retrieval before asking the user

## Communication Style
- Concise and direct
- Use bullet points for status updates
- Flag uncertainties explicitly

## Domain Knowledge
- [List relevant domain areas]
- [Reference any specific skills or tools]
```

SOUL.md authoring patterns:

| Pattern | Description | Example |
|---------|-------------|---------|
| Role-first | Start with "You are a ..." | "You are a Product Manager" |
| Constraint-driven | List behavioral rules | "Always verify tool output" |
| Communication | Define tone and style | "Concise, bullet points preferred" |
| Domain | Scope of knowledge | "Familiar with Scrum, Jira, roadmapping" |

### Step 3: Install common skills

```bash
# Install skills from the company-os repo
ln -s /path/to/company-os/skills/<skill-name> ~/.hermes/profiles/<profile-name>/skills/
```

### Step 4: Enable and start the gateway

```bash
# Enable systemd service
systemctl --user enable hermes-gateway@<profile-name>.service
systemctl --user start hermes-gateway@<profile-name>.service

# Verify
systemctl --user status hermes-gateway@<profile-name>.service
```

### Step 5: Create profile cron jobs

```bash
# Switch to profile context
hermes --profile <profile-name> cron create \
  --name "Daily Task" \
  --schedule "0 9 * * *" \
  --prompt "Your prompt here" \
  --skills "relevant-skill" \
  --deliver origin
```

### Step 6: Link shared scripts

```bash
# Symlink shared scripts from main ~/.hermes/scripts/
for script in restart-profile-gateway.sh gateway-signal-monitor.sh; do
    ln -s ~/.hermes/scripts/$script ~/.hermes/profiles/<profile-name>/scripts/
done
```

## Cron Jobs

No cron jobs needed for this recipe itself — it's the infrastructure for creating profiles. Each profile gets its own cron jobs as part of profile-specific recipes.

## Config

### Profile config.yaml template

```yaml
profile:
  name: "<profile-name>"
  description: "<description>"

model:
  default: <model-name>
  provider: <provider-type>
  base_url: <api-endpoint>
  api_key: ${API_KEY_ENV_VAR}
  api_mode: chat_completions

gateway:
  port: 0
  host: "127.0.0.1"

delivery:
  default: local
  fallback: local

tools:
  enabled:
    - terminal
    - file
    - search
    - web
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Gateway won't start for profile | Check config.yaml syntax: `hermes --profile <name> config validate` |
| Profile can't find scripts | Ensure scripts/ symlinks are valid |
| SOUL.md not being used | Verify it's in the correct location: `profiles/<name>/SOUL.md` |
| Wrong model being used | Check `model:` section in config.yaml — profile config overrides main config |
| Cron jobs not firing | Profile cron jobs must be created with `hermes --profile <name> cron` |
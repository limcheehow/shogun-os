# Company OS — Hermes Skill Tap Manifest

This repository is a [Hermes Agent skill tap](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills#publishing-a-custom-skill-tap).
Add it as a custom skill source to install Company OS skills directly.

## Add as a Tap

```bash
hermes skills tap add limcheehow/company-os
```

## Install Skills

```bash
# Browse available skills
hermes skills search --source limcheehow/company-os

# Install specific skills
hermes skills install limcheehow/company-os/department-scrum
hermes skills install limcheehow/company-os/brain-ingest-pipeline
```

## Skills Available

| Skill | Description |
|-------|-------------|
| `department-scrum` | Cross-department 3-tier daily scrum workflow (9am/11am/5pm) |
| `brain-ingest-pipeline` | Unified COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE data pipeline |

## Repository Structure

```
skills/
├── department-scrum/
│   ├── SKILL.md
│   ├── references/
│   ├── templates/
│   └── scripts/
└── brain-ingest-pipeline/
    ├── SKILL.md
    └── scripts/
```

## About

Company OS is a reference architecture for running an organization through Hermes Agent. Each department gets a dedicated AI agent with role-specific tools, memory, and autonomy.

See the [full repo](https://github.com/limcheehow/company-os) for profiles, templates, install scripts, and documentation.
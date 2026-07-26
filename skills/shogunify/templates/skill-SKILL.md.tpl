---
name: {{SKILL_NAME}}
description: "Use when {{TRIGGER}}. {{ONE_LINE_BEHAVIOR}}."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [{{TAGS}}]
    category: {{CATEGORY}}
    related_skills: []
---

# {{TITLE}}

## Overview

{{OVERVIEW}}

## When to Use

- {{TRIGGER_1}}
- {{TRIGGER_2}}

Don't use for: {{COUNTER_TRIGGERS}}

## Prerequisites

- Owning profile: `{{PROFILE}}`
- Env: {{ENV_VARS}}
- MCP / tools: {{TOOLS}}

## Workflows

### {{WORKFLOW_1_NAME}}

1. {{STEP_1}} — done when: {{CRITERION_1}}
2. {{STEP_2}} — done when: {{CRITERION_2}}

## Common Pitfalls

1. {{PITFALL_1}}

## Verification Checklist

- [ ] Skill installed under owning profile `skills/{{SKILL_NAME}}/`
- [ ] `/{{SKILL_NAME}}` loads on that profile
- [ ] Happy-path workflow completed once

# Task Management Schema

Unified task system used by ALL departments. One schema, department-specific grouping.

## Core Schema

Every task across all departments uses these fields:

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `type` | string | ✅ fixed | `task` |
| `title` | string | ✅ | What needs to be done |
| `description` | string | ❌ | Details, notes, links |
| `status` | enum | ✅ | `backlog`, `todo`, `in_progress`, `review`, `blocked`, `done`, `cancelled` |
| `priority` | enum | ✅ | `critical`, `high`, `medium`, `low` |
| `assignee` | string | ✅ | Staff slug or name |
| `due_date` | date | ❌ | YYYY-MM-DD |
| `group` | string | ✅ | The thing this task belongs to (project name, ticket ID, etc.) |
| `group_type` | enum | ✅ | `project`, `epic`, `ticket`, `initiative`, `campaign`, `audit` |
| `department` | string | ✅ | Which profile owns this task |
| `created_at` | datetime | auto | ISO 8601 |
| `updated_at` | datetime | auto | ISO 8601 |
| `tags` | string[] | ❌ | Free-form labels |
| `custom_fields` | object | ❌ | Department-specific extensions |

## Department-Specific Config

### `group_type` by Department

| Profile | group_type | Example | Custom Fields |
|---------|-----------|---------|---------------|
| Projects | `project` | "IOI Project" | milestone, customer |
| Procurement | `project` | "IOI Project" | vendor, po_number |
| Product | `epic` | "Dashboard v3" | feature, story_points |
| Customer Support | `ticket` | "TS-2026-001" | customer, severity |
| HR | `initiative` | "Q3 Hiring Drive" | role |
| Finance | `initiative` | "Annual Audit" | budget_code |
| Marketing | `campaign` | "Edge AI Launch" | channel |
| Compliance | `audit` | "ISO Recert" | framework |
| Coding | `epic` | "Auth Refactor" | repo |

### Custom Fields Schema

```yaml
projects:
  milestone: string      # Project milestone phase
  customer: string       # Customer name

procurement:
  vendor: string          # Vendor/supplier name
  po_number: string       # Purchase order reference

product:
  feature: string         # Related feature name
  story_points: integer   # Effort estimate

customer_support:
  customer: string        # Client name
  severity: enum          # critical, high, medium, low

hr:
  role: string            # Position/hiring role

finance:
  budget_code: string     # Budget category reference

marketing:
  channel: string         # Campaign channel (email, social, event)

compliance:
  framework: string       # Compliance framework (ISO 27001, etc.)

coding:
  repo: string            # GitHub repository name
```

## Status Lifecycle

```
backlog ──→ todo ──→ in_progress ──→ review ──→ done
              │            │             │
              └─────→ blocked ←──────────┘
                         │
                         └─────→ cancelled
```

- `backlog` → `todo`: Prioritized for current cycle
- `todo` → `in_progress`: Work started
- `in_progress` → `review`: Ready for review
- `review` → `done`: Approved and complete
- `in_progress` → `blocked`: Dependency unmet
- `blocked` → `in_progress`: Unblocked
- Any → `cancelled`: No longer relevant

## Brain Page Format

Tasks are stored as gbrain pages with `type: task`:

```markdown
---
type: task
title: "Configure GPU cluster for IOI project"
status: in_progress
priority: high
assignee: "ali-baba"
due_date: 2026-07-15
group: "IOI Project"
group_type: project
department: projects
tags: [infrastructure, deployment, gpu]
custom_fields:
  milestone: "Phase 2 - Deployment"
  customer: "IOI Corporation"
---

## Description

Set up the GPU cluster for IOI's edge AI deployment.

## Updates

- 2026-06-21 | Started procurement of NVIDIA GPUs
- 2026-06-22 | Vendor confirmed delivery timeline
```

## Queries

Common task queries across departments:

```bash
# My tasks
gbrain query "type:task assignee:current_user status:todo|in_progress"

# Blocked tasks
gbrain query "type:task status:blocked"

# Overdue
gbrain query "type:task due_date:<today status:todo|in_progress"

# Department backlog
gbrain query "type:task status:backlog department:projects"

# Group tasks
gbrain query "type:task group:\"IOI Project\""
```

## Shared Skill

The unified task management shared skill is at `skills/shared/task-management/SKILL.md`.
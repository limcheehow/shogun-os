---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Project Management Provider Contract

> **Standard tool names and response shapes for project management integrations.**
> Covers projects, tasks, milestones, and time tracking.

## Tools

### proj_list_projects

List projects.

**Input:** `{ "search": "string", "status": "string (active | archived | all)", "owner": "string", "limit": 50 }`

**Output:** `{ "projects": [{ "id": "string", "name": "string", "description": "string", "status": "string", "owner": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "progress_pct": 0, "task_count": 0, "completed_count": 0 }], "total": 0 }`

### proj_list_tasks

List tasks with filters.

**Input:** `{ "project_id": "string", "assignee": "string", "status": "string (todo | in_progress | done | all)", "priority": "string (low | medium | high | critical)", "milestone_id": "string", "limit": 50 }`

**Output:** `{ "tasks": [{ "id": "string", "title": "string", "status": "string", "priority": "string", "assignee": "string", "project_id": "string", "project_name": "string", "milestone_id": "string", "due_date": "YYYY-MM-DD", "estimated_hours": 0, "logged_hours": 0, "labels": ["string"] }], "total": 0 }`

### proj_create_task

Create a new task.

**Input:** `{ "project_id": "string (required)", "title": "string (required)", "description": "string", "assignee": "string", "priority": "string", "due_date": "YYYY-MM-DD", "estimated_hours": 0, "labels": ["string"] }`

**Output:** `{ "id": "string", "title": "string", "status": "todo" }`

### proj_update_task

Update task status, assignee, or priority.

**Input:** `{ "id": "string (required)", "status": "string", "assignee": "string", "priority": "string", "description": "string", "due_date": "YYYY-MM-DD" }`

**Output:** `{ "id": "string", "status": "string" }`

### proj_list_milestones

List milestones.

**Input:** `{ "project_id": "string (required)", "status": "string (upcoming | achieved | all)", "limit": 50 }`

**Output:** `{ "milestones": [{ "id": "string", "name": "string", "description": "string", "status": "string", "due_date": "YYYY-MM-DD", "progress_pct": 0, "task_count": 0, "completed_count": 0 }], "total": 0 }`

### proj_get_project_timeline

Get project timeline / Gantt data.

**Input:** `{ "project_id": "string (required)" }`

**Output:** `{ "project_id": "string", "project_name": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "milestones": [{ "name": "string", "date": "YYYY-MM-DD" }], "tasks": [{ "id": "string", "title": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "duration_days": 0, "dependencies": ["string"], "assignee": "string", "progress_pct": 0 }] }`

## Error Response Shape

All tools return `{"error": "string", "code": "..."}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `proj_list_projects` | P0 |
| `proj_list_tasks` | P0 |
| `proj_create_task` | P0 |
| `proj_update_task` | P0 |
| `proj_list_milestones` | P1 |
| `proj_get_project_timeline` | P1 |
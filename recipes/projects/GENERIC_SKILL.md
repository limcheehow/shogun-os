---
name: projects-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# Project Management Skill (Generic)

> **Works with any project management provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `projects` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List active projects"
1. Call `proj_list_projects(status=active)`
2. Format as table: Project | Owner | Progress | Tasks | Due Date

### "List my tasks"
1. Call `proj_list_tasks(assignee=me, status=todo|in_progress)`
2. Sort by priority then due date
3. Flag overdue tasks

### "Create a task"
1. Gather: project, title, assignee, priority, due date
2. Call `proj_create_task` with structured data
3. Confirm with task ID

### "Update task status"
1. Call `proj_update_task(id=..., status=...)`
2. Confirm the status change

### "Project timeline"
1. Call `proj_get_project_timeline(project_id=...)`
2. Report milestones, task dependencies, and critical path
3. Flag overdue tasks and upcoming milestones

### "Check milestones"
1. Call `proj_list_milestones(project_id=..., status=upcoming)`
2. List upcoming milestones with due dates and progress

## Cron Job Templates

**Project status** (Monday 9AM):
```bash
hermes cron create "0 9 * * 1" --name "Project Status" --prompt "Check all active projects using proj_list_projects. For each project, report progress, upcoming milestones, and overdue tasks." --skill "projects-provider" --deliver origin
```
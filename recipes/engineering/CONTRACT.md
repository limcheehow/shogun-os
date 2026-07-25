---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Engineering Provider Contract

> **Standard tool names and response shapes for engineering/DevOps integrations.**
> Covers code repositories, issues, pull requests, CI/CD, and deployments.

## Tools

### eng_list_repos

List code repositories.

**Input:** `{ "search": "string", "organization": "string", "visibility": "string (public | private | all)", "limit": 50 }`

**Output:** `{ "repos": [{ "id": "string", "name": "string", "full_name": "string", "description": "string", "language": "string", "default_branch": "string", "visibility": "string", "updated_date": "ISO 8601", "open_issues": 0, "stars": 0 }], "total": 0 }`

### eng_list_issues

List issues/PRs with filters.

**Input:** `{ "repo": "string (required)", "state": "string (open | closed | all)", "type": "string (issue | pr | all)", "assignee": "string", "label": "string", "milestone": "string", "sort": "string (created | updated | comments)", "limit": 50 }`

**Output:** `{ "issues": [{ "id": "string", "number": 0, "title": "string", "state": "string", "type": "string", "assignee": "string", "labels": ["string"], "milestone": "string", "created_date": "ISO 8601", "updated_date": "ISO 8601", "url": "string" }], "total": 0 }`

### eng_create_issue

Create a new issue.

**Input:** `{ "repo": "string (required)", "title": "string (required)", "body": "string", "assignee": "string", "labels": ["string"], "milestone": "string" }`

**Output:** `{ "id": "string", "number": 0, "title": "string", "url": "string" }`

### eng_list_prs

List pull requests (alias for eng_list_issues with type=pr).

**Input:** `{ "repo": "string (required)", "state": "string (open | closed | merged | all)", "assignee": "string", "limit": 50 }`

**Output:** `{ "prs": [{ "id": "string", "number": 0, "title": "string", "state": "string", "author": "string", "assignee": "string", "source_branch": "string", "target_branch": "string", "created_date": "ISO 8601", "updated_date": "ISO 8601", "mergeable": true, "review_count": 0, "ci_status": "string (passing | failing | pending)" }], "total": 0 }`

### eng_list_workflows

List CI/CD workflow runs.

**Input:** `{ "repo": "string (required)", "branch": "string", "status": "string (success | failure | running | all)", "limit": 20 }`

**Output:** `{ "workflows": [{ "id": "string", "name": "string", "status": "string", "branch": "string", "trigger": "string", "started_date": "ISO 8601", "duration_seconds": 0, "url": "string" }], "total": 0 }`

### eng_list_deployments

List recent deployments.

**Input:** `{ "repo": "string (required)", "environment": "string (production | staging | all)", "status": "string (success | failure | all)", "limit": 20 }`

**Output:** `{ "deployments": [{ "id": "string", "environment": "string", "status": "string", "branch": "string", "commit_sha": "string", "deployed_at": "ISO 8601", "deployed_by": "string", "url": "string" }], "total": 0 }`

## Error Response Shape

All tools return `{"error": "string", "code": "..."}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `eng_list_repos` | P0 |
| `eng_list_issues` | P0 |
| `eng_create_issue` | P0 |
| `eng_list_prs` | P0 |
| `eng_list_workflows` | P1 |
| `eng_list_deployments` | P1 |
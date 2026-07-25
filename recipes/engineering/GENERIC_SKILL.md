---
name: engineering-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# Engineering Skill (Generic)

> **Works with any engineering provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `engineering` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List open issues"
1. Call `eng_list_issues(repo=..., state=open)` for a specific repo
2. Format as table: # | Title | Assignee | Labels | Updated

### "Create an issue"
1. Gather: repo, title, description, assignee, labels
2. Call `eng_create_issue` with structured data
3. Confirm with issue number and URL

### "Review open pull requests"
1. Call `eng_list_prs(repo=..., state=open)`
2. Report: PR count, CI status, review count per PR
3. Flag PRs with failing CI or no reviews for >2 days

### "Check CI/CD status"
1. Call `eng_list_workflows(repo=..., branch=main, status=...)`
2. Report latest workflow runs, flag failures

### "Recent deployments"
1. Call `eng_list_deployments(repo=..., limit=10)`
2. List recent deployments with environment, status, and branch

## Cron Job Templates

**PR review reminder** (daily 9AM):
```bash
hermes cron create "0 9 * * 1-5" --name "PR Review Reminder" --prompt "Check open PRs across repos using eng_list_prs. Flag PRs with no reviews for >2 days or failing CI. List PRs ready for review." --skill "engineering-provider" --deliver origin
```

**Deployment summary** (Monday 8AM):
```bash
hermes cron create "0 8 * * 1" --name "Deployment Summary" --prompt "Check last week's deployments using eng_list_deployments. Report deployment count by environment and any failures." --skill "engineering-provider" --deliver origin
```
# HR Staff Directory — Generic Skill

Load this skill when you need to synchronize staff data from an HRMS provider. It uses the provider abstraction pattern — the user selects which provider (BrioHR, BambooHR, etc.) and the skill calls the appropriate bridge.

## Triggers

- "sync staff from HRMS"
- "update employee directory"
- "import staff from briohr"
- "run HR sync"

## Workflow

1. Identify which HRMS provider the user has configured
2. Call `hr_sync_employees()` to fetch all employees
3. Call `hr_sync_leave_balances()` to fetch leave data
4. For each employee, write a brain page to `shared/staff/{slug}.md`
5. Report summary: created, updated, skipped

## Tool Names

This skill uses the following tool names across all providers:

| Tool | Returns | Description |
|---|---|---|
| `hr_sync_employees` | `Employee[]` | Full employee list |
| `hr_sync_leave_balances` | `LeaveBalance[]` | Leave balances |
| `hr_lookup_employee(email)` | `Employee\|null` | Single lookup |

## Reference

- Contract: `recipes/hr/staff-directory/CONTRACT.md`
- BrioHR reference: `recipes/hr/staff-directory/providers/briohr.md`
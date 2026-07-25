---
id: provider-abstraction-architecture
name: Provider Abstraction Architecture
version: 1.0.0
description: >
  Define standard API contracts for domain actions (time tracking, HR, etc.)
  so users can bring any provider that implements the contract. Ship reference
  bridges. Write generic skills. Let users plug in.
category: architecture
requires: []
secrets: []
health_checks: []
setup_time: 15 min
cost_estimate: "$0 (reference bridges ship with repo)"
---

# Provider Abstraction Architecture

> **Let users bring their own backends to any agent profile, as long as the backend implements the required API contract.**

Currently, every provider integration is hardcoded. Jibble → Jibble API calls in the Jibble skill. Kami → Kami API calls if we wrote one. This doesn't scale — every provider needs its own skill, and adding a new one means rewriting agent workflows.

## The Pattern: Contract-First Provider Abstraction

```
┌──────────────────────────────────────────────────────────────┐
│                    Hermes Agent Profile                      │
│                                                              │
│  ┌─────────────────────┐   ┌─────────────────────────────┐  │
│  │  Generic Skill       │   │  Cron Templates             │  │
│  │  "tt_current_status" │   │  (use same tool names)      │  │
│  │  "tt_get_entries"    │   │                             │  │
│  │  "tt_crud_projects"  │   └─────────────────────────────┘  │
│  └──────────┬──────────┘                                      │
│             │                                                  │
│  ┌──────────▼──────────┐                                      │
│  │  MCP Bridge Layer   │    ← User picks ONE of these         │
│  │                     │                                       │
│  │  ┌────────────────┐ │                                       │
│  │  │ jibble-bridge  │ │  ✓ Ships with repo                   │
│  │  ├────────────────┤ │                                       │
│  │  │ kami-bridge    │ │  ✓ Community/provider contributed     │
│  │  ├────────────────┤ │                                       │
│  │  │ hubstaff-bridge│ │  ✓ Community/provider contributed     │
│  │  ├────────────────┤ │                                       │
│  │  │ custom-bridge  │ │  ✗ User writes their own             │
│  │  └────────────────┘ │                                       │
│  └──────────▲──────────┘                                      │
│             │                                                  │
└─────────────┼──────────────────────────────────────────────┘
              │
  ┌───────────┴───────────┐
  │  Provider API (any)   │
  │  Jibble / Kami /      │
  │  Hubstaff / Custom    │
  └───────────────────────┘
```

## Three Layers

### Layer 1: Standard Contract (MCP Tool Names)

Define a set of **standard tool names** for each domain. These are what the generic skill uses. The bridge maps these to real API calls.

**Time Tracking Contract** (`tt_*`) — located at `recipes/hr/time-tracking/CONTRACT.md`:

| Standard Tool | Purpose | Required Fields |
|--------------|---------|-----------------|
| `tt_clock_in` | Clock in with GPS | `memberId`, `latitude`, `longitude`, `timestamp` |
| `tt_clock_out` | Clock out | `memberId`, `timestamp` |
| `tt_current_status` | Who's clocked in now | (none — returns list of active) |
| `tt_get_entries` | Time entries by date | `from`, `to`, `memberId?`, `projectId?` |
| `tt_get_members` | List team members | (none — returns member list) |
| `tt_get_projects` | List projects | (none — returns project list) |
| `tt_create_project` | Create a project | `name`, `description?`, `budget?` |
| `tt_update_project` | Update a project | `projectId`, `name?`, `description?` |
| `tt_delete_project` | Archive/disable project | `projectId` |

**Accounting Contract** (`acct_*`) — located at `recipes/accounting/CONTRACT.md`:

| Standard Tool | Purpose | Required Fields |
|--------------|---------|-----------------|
| `acct_list_sales_invoices` | List sales invoices | `search?`, `contact_id?`, `date_from?`, `date_to?`, `status?` |
| `acct_create_sales_invoice` | Create sales invoice | `contact_id`, `date`, `payment_mode`, `status`, `tax_mode` |
| `acct_list_purchase_bills` | List purchase bills | `search?`, `contact_id?`, `date_from?`, `date_to?` |
| `acct_create_purchase_bill` | Create purchase bill | `contact_id`, `date`, `payment_mode`, `status`, `tax_mode` |
| `acct_list_contacts` | List customers/vendors | `type?`, `search?` |
| `acct_create_contact` | Create customer/vendor | `name`, `type` |
| `acct_list_products` | List products/services | `search?` |
| `acct_get_profit_loss` | Get P&L summary | `date_from`, `date_to` |
| `acct_get_balance_sheet` | Get balance sheet | `as_of_date?` |
| `acct_get_aging_report` | Get AR/AP aging | `type` (receivable/payable) |
| `acct_update_invoice_status` | Update invoice status | `id`, `type`, `status` |

**HR Leave Contract** (`leave_*`):

| Standard Tool | Purpose |
|--------------|---------|
| `leave_balance` | Get leave balance for member |
| `leave_apply` | Submit leave request |
| `leave_calendar` | Who's on leave today |
| `leave_approve` | Approve pending leave |

**Expense Contract** (`exp_*`):

| Standard Tool | Purpose |
|--------------|---------|
| `exp_submit` | Submit expense with receipt |
| `exp_list` | List expenses by date/member |
| `exp_approve` | Approve pending expense |
| `exp_categories` | List expense categories |

### Layer 2: Generic Hermes Skill

The skill ships with the repo and works with ANY provider. It never references specific API names — only the standard contract tool names.

```markdown
# Time Tracking Skill (Generic)

## Workflows

### "Who's clocked in today?"
1. Call `tt_current_status`
2. For each active member, fetch name via `tt_get_members`
3. Format as: [✅ Name] — clocked in at HH:MM
4. Flag anyone expected but missing

### "Show yesterday's timesheet"
1. Call `tt_get_entries(from=yesterday, to=yesterday)`
2. Group by member
3. Calculate total hours per member
4. Format as a table with: Member | Clock In | Clock Out | Total Hours

### "Weekly attendance summary"
1. Call `tt_get_entries(from=mon, to=sun)`
2. Aggregate by member across the week
3. Flag missing days, late arrivals, overtime
4. Deliver formatted report

### "Create new project"
1. Call `tt_create_project(name=..., description=...)`
2. Verify project exists via `tt_get_projects`
3. Log to gbrain under the department's source
```

### Layer 3: Provider-Specific MCP Bridges

Each bridge is a thin Python script that:
1. Reads the provider's API key from environment
2. Implements the standard MCP protocol over stdio
3. Maps standard tool calls → provider-specific REST API calls
4. Maps provider responses → standard response shape

#### Jibble Bridge (`scripts/tt-bridge-jibble.py`)

Already exists in concept in the current recipe. Just needs to be renamed to use standard tool names.

```python
# Minimal example of the mapping pattern:
if tool == "tt_current_status":
    # Jibble: GET /v1/entries?status=active
    resp = call_jibble("/entries", {"status": "active"})
    return {"active": [m for m in resp if m["isActive"]]}

if tool == "tt_get_entries":
    # Jibble: GET /v1/entries?from=X&to=Y
    resp = call_jibble("/entries", {"from": args["from"], "to": args["to"]})
    return resp
```

#### Kami Bridge (`scripts/tt-bridge-kami.py`)

Same standard tools, different API endpoints:

```python
if tool == "tt_current_status":
    # Kami: GET /api/v1/attendance/active
    resp = call_kami("/attendance/active")
    return resp

if tool == "tt_get_entries":
    # Kami: GET /api/v1/attendance?start=X&end=Y
    resp = call_kami("/attendance", {"start": args["from"], "end": args["to"]})
    return resp
```

## User Experience

### How a User Configures Their Provider

1. **Pick a provider** — Jibble, Kami, Hubstaff, or a custom one
2. **Get API key** — from the provider's dashboard
3. **Configure the MCP bridge** — add to profile config:

```yaml
mcp_servers:
  time-tracking:
    command: python3
    args:
      - ~/.hermes/scripts/tt-bridge-jibble.py
    env:
      TT_API_KEY: "${TT_API_KEY}"
      TT_BASE_URL: "https://api.jibble.io/v1"
```

4. **Set the API key** in the profile's `.env`:

```bash
TT_API_KEY=sk-your-jibble-or-kami-key
```

5. **Done** — the generic time tracking skill in the profile already knows how to use `tt_*` tools. No skill changes needed.

### How a User Adds a New Provider

If the provider isn't Jibble (which ships as reference), the user:

1. Writes a thin bridge script (or finds one contributed by the community)
2. Places it in `~/.hermes/scripts/tt-bridge-<provider>.py`
3. Configures the MCP server (same pattern, just different `args` and `env`)
4. Every generic skill works immediately

## What Ships in the Repo

```
recipes/
├── hr/time-tracking/                      # Time tracking provider abstraction
│   ├── CONTRACT.md
│   ├── GENERIC_SKILL.md
│   ├── bridges/
│   │   └── tt-bridge-jibble.py
│   └── providers/
│       ├── jibble.md
│       └── kami.md
├── accounting/                            # Accounting provider abstraction
│   ├── CONTRACT.md
│   ├── GENERIC_SKILL.md
│   ├── bridges/
│   │   └── acct-bridge.py                 # Unified bridge (plugin loader)
│   ├── plugins/
│   │   ├── bukku.py
│   │   ├── quickbooks.py
│   │   └── xero.py
│   ├── oauth-helper.py                    # Shared OAuth2 helper
│   └── providers/
│       ├── bukku.md
│       ├── quickbooks.md
│       └── xero.md
```

## Benefits

| Before (Hardcoded) | After (Abstracted) |
|--------------------|--------------------|
| One skill per provider | One generic skill, N bridges |
| Adding a provider = rewrite skill | Adding a provider = write bridge (50 lines) |
| User locked to chosen provider | User can swap without changing agent behavior |
| Skill references Jibble API names | Skill references standard contract names |
| Cron prompts hardcoded to provider | Cron prompts use standard tools |

## Future: MCP Provider Registry

For scale, this could become a registry pattern:

```
hermes tt provider add jibble       # Installs bridge + configures MCP
hermes tt provider add kami
hermes tt provider switch kami      # Swap backend without touching skills
hermes tt test                      # Verify all standard tools work
```

That's a longer-term addition. The architecture above works with zero changes to Hermes itself — just pure MCP + skill design.

---

## How-To Guide

For a step-by-step walkthrough with examples, see
[`docs/recipes/creating-provider-abstractions.md`](../recipes/creating-provider-abstractions.md).
It covers:

- Creating a new domain abstraction from scratch
- Adding multiple connectors to a single department profile
- Adding a new provider to an existing domain
- Full lifecycle checklist for repo contributions
---
id: creating-provider-abstractions
name: Creating Provider Abstractions
version: 1.0.0
description: >
  Step-by-step guide to creating new domain provider abstractions and
  adding multiple connectors per department in Shogun OS.
category: architecture
setup_time: 20 min
cost: $0
depends_on: []
---

# Creating Provider Abstractions

> **How to create a new domain abstraction (CONTRACT + GENERIC_SKILL) and
> how to wire multiple provider connectors into a single department profile.**

> **Prefer `/shogunify` for day-to-day scaffolding.** See
> [`shogunify.md`](shogunify.md) for the agent-facing questionnaire
> (profile-aware install, skill/connector/workflow modes). Use this guide
> for deep provider-abstraction edge cases (OAuth cache layout, importlib
> pitfalls, multi-connector profiles).

## Architecture Recap

Every provider abstraction in Shogun OS follows a three-layer pattern:

```
recipes/<domain>/
├── CONTRACT.md         # Standard tool interface (tool names, I/O shapes)
├── GENERIC_SKILL.md    # Agent skill — works with ANY provider
├── bridges/            # MCP bridge scripts (one per provider, or unified)
├── plugins/            # Provider plugins (for unified bridges)
└── providers/          # Provider-specific setup docs
```

Each profile activates its abstractions via MCP server config in `config.yaml`.
The agent reads the GENERIC_SKILL and knows how to use the standard tools —
regardless of which backend provider is configured.

---

## Part 1: Creating a New Domain Abstraction

### Step 1: Define the Contract (`CONTRACT.md`)

Identify the core domain operations. For a new domain, define 5-10 standard
tools that cover the most common workflows. Tools should be:

- **Provider-agnostic** — no provider-specific naming (e.g., use `acct_list_contacts`, not `acct_list_bukku_contacts`)
- **Minimal but complete** — cover the P0 workflows (list, create, update) in a few tools
- **Consistent shapes** — use the same response envelope pattern across all tools

**Naming convention:** `<domain>_<verb>_<noun>` where domain is a short prefix:

| Domain | Prefix | Profile |
|--------|:------:|---------|
| Time tracking | `tt_` | HR |
| Accounting | `acct_` | Finance |
| Procurement | `proc_` | Procurement |
| CRM | `crm_` | CRM |
| Marketing | `mkt_` | Marketing |
| Compliance | `comp_` | Compliance |
| Support | `spt_` | Support |
| Engineering | `eng_` | Coding |
| Projects | `proj_` | Projects |
| Product | `pd_` | Product |

**Minimum P0 tools for any domain:**

1. `list_<entities>` — list with filters (search, date range, status, limit)
2. `create_<entity>` — create with required fields
3. `update_<entity>` — update status or fields
4. `get_<report>` — domain-specific report or summary

**Example CONTRACT.md structure:**

```markdown
---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# <Domain> Provider Contract

> **Standard tool names and response shapes for <domain> integrations.**

## Tools

### <domain>_list_<entities>

List with optional filters.

**Input:** `{ "search": "string", "status": "string", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50 }`

**Output:** `{ "<entities>": [{ "id": "string", ... }], "total": 0 }`

### <domain>_create_<entity>

Create a new entity.

**Input:** `{ "<field>": "string (required)", ... }`

**Output:** `{ "id": "string", "status": "string" }`

## Error Response

All tools return `{"error": "string", "code": "MISSING_FIELD | AUTH_FAILED | RATE_LIMITED | NOT_FOUND | PROVIDER_ERROR"}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `<domain>_list_<entities>` | P0 |
| `<domain>_create_<entity>` | P0 |
```

### Step 2: Create the Generic Skill (`GENERIC_SKILL.md`)

The GENERIC_SKILL teaches the agent how to use the standard tools. It never
references provider-specific names — only the CONTRACT tool names.

**Structure:**

```markdown
---
name: <domain>-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# <Domain> Skill (Generic)

> **Works with any <domain> provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `<domain>` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List <entities>"
1. Call `<domain>_list_<entities>` with optional filters
2. Format as table with key fields

### "Create <entity>"
1. Gather required fields
2. Call `<domain>_create_<entity>` with structured data
3. Confirm with returned ID

### "Search for <entity>"
1. Call `<domain>_list_<entities>(search=...)` 
2. Return matching results or create if not found

## Cron Job Templates

**Daily <domain> check:**
\`\`\`bash
hermes cron create "0 9 * * *" --name "<Domain> Check" --prompt "..." --skill "<domain>-provider" --deliver origin
\`\`\`
```

### Step 3: Choose a Bridge Strategy

Shogun OS supports two bridge strategies:

| Strategy | When to Use | Example |
|----------|-------------|---------|
| **Unified bridge** (plugin-based) | Multiple providers expected, same contract tools | Accounting (Bukku, QBO, Xero) |
| **Per-provider bridge** | Single reference provider, or very different APIs | Time tracking (Jibble bridge) |

**Unified bridge** (`bridges/<domain>-bridge.py`):

```python
import importlib, os, json, sys
PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins"
PROVIDER = os.environ.get("<DOMAIN>_PROVIDER", "default")

def load_provider(name):
    spec = importlib.util.spec_from_file_location(name, PLUGIN_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Standard MCP loop: tools/list → tools/call
```

**Provider plugins** (`plugins/<provider>.py`):

```python
def get_tool_schemas():
    return [{"name": "...", "inputSchema": {...}}, ...]

def handle_tool(name, args):
    if name == "<domain>_list_<entities>": return _list(args)
    elif name == "<domain>_create_<entity>": return _create(args)
```

### Step 4: Write Provider Setup Docs

Create `providers/<provider>.md` for each supported provider:

- Where to get API credentials
- MCP server config snippet
- Env vars to set
- Verify command

### Step 5: Wire into a Profile

Update the profile's `config.yaml` in `templates/profiles/`:

```yaml
mcp_servers:
  <domain>:
    command: python3
    args: [~/.hermes/scripts/<domain>-bridge.py]
    env:
      <DOMAIN>_PROVIDER: "${<DOMAIN>_PROVIDER}"
      <DOMAIN>_API_KEY: "${<DOMAIN>_API_KEY}"
```

Update `PROFILE_CATALOG.md` to add the skill name to the profile's Skills row.
Update `scripts/generate-profile.py` to include the skill in the profile type's `skills` list.
Update `RECIPE_INDEX.md` with a new entry for the domain.

---

## Part 2: Multiple Connectors Per Department

A single department profile can activate **multiple provider abstractions**
simultaneously. Each abstraction has its own MCP server and GENERIC_SKILL.

### Example: HR Profile with 3 Connectors

The HR profile (Jinzai) can have:

| MCP Server | Contract | Generic Skill | Provider | Purpose |
|------------|----------|---------------|----------|---------|
| `time-tracking` | `tt_*` | `time-tracking` | Jibble / Kami | Attendance, timesheets |
| `hr-leave` | `leave_*` | `hr-leave-provider` | Kakitangan / PayrollPanda | Leave balance, applications |
| `hr-payroll` | `payroll_*` | `hr-payroll-provider` | PayrollPanda / others | Salary, payslips, EPF |

### Config for Multiple Connectors

The HR profile's `config.yaml` simply lists multiple MCP servers:

```yaml
mcp_servers:
  time-tracking:
    command: python3
    args: [~/.hermes/scripts/tt-bridge-jibble.py]
    env:
      TT_API_KEY: "${TT_API_KEY}"
  
  hr-leave:
    command: python3
    args: [~/.hermes/scripts/hr-bridge.py]
    env:
      HR_PROVIDER: "${HR_PROVIDER}"
      HR_API_KEY: "${HR_API_KEY}"
```

The profile's SOUL.md tells the agent which skills it has:

```markdown
## Your Skills
- `time-tracking` — Track attendance, clock-in/out, timesheets
- `hr-leave-provider` — Manage leave balances, applications, approvals
- `hr-payroll-provider` — Payroll processing, payslips, EPF/SOCSO
```

### The SOUL.md as Integration Hub

The SOUL.md is the key file that tells the agent what connectors it has.
Each connector listed in SOUL.md should correspond to an MCP server in
config.yaml and a GENERIC_SKILL that the agent can load.

### Cron Jobs Across Multiple Connectors

Cron jobs can reference multiple skills when they need to combine data:

```bash
hermes cron create "30 9 * * 1-5" \
  --name "HR Morning Briefing" \
  --prompt "Run daily attendance check (tt_current_status), check who's on leave (leave_calendar), and flag any late arrivals." \
  --skill "time-tracking,hr-leave-provider" \
  --deliver origin
```

### Pattern: Department with the Most Connectors

| Department | Connectors | Profile |
|------------|------------|---------|
| **HR** | Time tracking, Leave, Payroll, ATS, Training | `hr-manager` |
| **Finance** | Accounting (Bukku/QBO/Xero), Expense, Budget | `finance-manager` |
| **CRM** | Deals, Contacts, Activities, Email, Comms platform | `crm-manager` |
| **Engineering** | Repos, Issues, PRs, CI/CD, Deployments, Monitoring | `coding-agent` |
| **Marketing** | Campaigns, Email, Social, Analytics, CMS | `marketing-manager` |

---

## Part 3: Full Lifecycle Checklist

When adding a new provider abstraction to the repo:

- [ ] `recipes/<domain>/CONTRACT.md` — Standard tool names and response shapes
- [ ] `recipes/<domain>/GENERIC_SKILL.md` — Agent-facing workflows
- [ ] `recipes/<domain>/bridges/<bridge>.py` — MCP bridge (unified or per-provider)
- [ ] `recipes/<domain>/plugins/<provider>.py` — Provider plugin (for unified bridges)
- [ ] `recipes/<domain>/providers/<provider>.md` — Setup docs per provider
- [ ] `templates/profiles/<profile-type>.yaml` — MCP server config (or update base-config.yaml)
- [ ] `scripts/generate-profile.py` — Add skill to profile type's `skills` list
- [ ] `PROFILE_CATALOG.md` — Add skill to the profile's Skills row
- [ ] `RECIPE_INDEX.md` — Add recipe entry and update installation order
- [ ] `CRON_INVENTORY.md` — Add cron job templates if applicable
- [ ] `llms.txt` — Add recipe to the table
- [ ] `HUB.md` — Add skill to the skills table
- [ ] `docs/architecture/PROVIDER_ABSTRACTION.md` — Add contract table (optional but recommended)
- [ ] `scripts/install.sh` — Update `section_recipes()` if it's a new directory
- [ ] `scripts/verify-install.sh` — Add check for the new abstraction

---

## Part 4: Adding a New Provider to an Existing Domain

If a domain abstraction already exists (e.g., accounting with Bukku) and you
want to add a new provider (e.g., QuickBooks):

1. **Create the plugin** — `recipes/accounting/plugins/quickbooks.py`
2. **Implement `get_tool_schemas()` and `handle_tool()`** — same contract tools, different API calls
3. **Write the provider doc** — `recipes/accounting/providers/quickbooks.md`
4. **Done** — the unified bridge auto-loads the plugin when `ACCT_PROVIDER=quickbooks`

No changes needed to:
- CONTRACT.md (tools are the same)
- GENERIC_SKILL.md (uses the same tool names)
- Profile templates (same MCP server config, just different env vars)
- RECIPE_INDEX.md (already listed)

---

## Part 5: Pitfalls & Lessons Learned

Real issues discovered during the accounting abstraction implementation.
Learn from these to avoid the same mistakes.

### 1. Plugin imports break with `importlib` loading

When the unified bridge loads a plugin via `importlib.util.spec_from_file_location()`,
the plugin's `sys.path` does **not** include the parent directory. Any shared
modules (like `oauth_helper.py`) in the parent directory will be unreachable.

**Fix:** In the bridge's `load_provider()`, add the parent directory to `sys.path`
before importing the plugin:

```python
sys.path.insert(0, str(PLUGIN_DIR.parent))
```

### 2. All imports at the top of every file

Python convention: all `import` statements go at the top of the file, before
any function definitions, constants, or logic. If you add an import during
development (e.g., `import traceback` for debugging), move it to the top
before committing. Mid-file imports work but violate PEP 8 and confuse
readers.

### 3. Provider-specific API fields differ from contract conventions

The contract defines generic fields (e.g., `date_from`, `date_to`), but each
provider API uses different field names for the same concept:

| Provider | Date field | Filter syntax |
|----------|-----------|---------------|
| Bukku | `date_from` / `date_to` | REST query params |
| QuickBooks | `TxnDate` | QBO SQL-like query language |
| Xero | `DateFrom` / `DateTo` | REST query params |

Always use the **user-facing date field** (e.g., `TxnDate` for invoice date),
not `MetaData.CreateTime` (creation timestamp). Users expect "invoices from
last month" to filter by invoice date, not creation date.

### 4. Report parsing is provider-specific and complex

QBO and Xero return financial reports (P&L, Balance Sheet) as nested row
structures, not flat JSON. The structure varies by provider:

**QBO report structure:**
```
Rows → Row[] (sections)
  ├── Header → ColData[] (section name)
  ├── Rows → Row[] (account rows)
  │   └── ColData[] (account name, value)
  └── Summary → ColData[] (section total)
```

**Xero report structure:**
```
Rows[] (sections)
  ├── Title (section name)
  └── Rows[] (account rows)
      └── Cells[] (Value for account name, amount)
```

**Common pitfalls when parsing reports:**
- Section names are not guaranteed to be consistent across locales/languages
- Sub-sections exist (nested rows) — the parser must handle depth
- Zero-value rows may be included or excluded
- Currency formatting (commas, symbols) must be stripped before `float()` conversion
- Some providers return `null` for zero values, others return `0`

**Recommendation:** Parse by section name substring matching (`"Income" in name`)
rather than exact match, and handle nested sections recursively.

### 5. Cross-provider edge cases

When a contract defines a field that maps differently across providers, test
every value. Example: `contact.type = "both"` in QuickBooks.

```python
# WRONG: elif means "both" never reaches the supplier branch
if args["type"] in ("customer", "both"):
    ...create customer...
    return ...  # ❌ Early return skips supplier creation

# RIGHT: independent if blocks for each type
if args["type"] in ("customer", "both"):
    ...create customer...
if args["type"] in ("supplier", "both"):
    ...create supplier...
```

### 6. MCP bridge env vars must list EVERYTHING

The MCP server config in `config.yaml` has an `env:` block that defines which
environment variables are passed to the bridge subprocess. If a provider plugin
reads an env var that is NOT listed in the `env:` block, it will get an empty
string.

**Bukku needs:** `ACCT_PROVIDER`, `ACCT_API_KEY`, `ACCT_SUBDOMAIN`
**QuickBooks needs:** `ACCT_PROVIDER`, `ACCT_API_KEY`, `ACCT_CLIENT_ID`, `ACCT_CLIENT_SECRET`, `ACCT_REFRESH_TOKEN`, `ACCT_COMPANY_ID`
**Xero needs:** `ACCT_PROVIDER`, `ACCT_API_KEY`, `ACCT_CLIENT_ID`, `ACCT_CLIENT_SECRET`, `ACCT_REFRESH_TOKEN`, `ACCT_TENANT_ID`

The `env:` block in the bridge config must include ALL of these, even if some
are only used by one provider. The MCP subprocess gets a **filtered**
environment — it does NOT inherit the parent shell's env vars.

### 7. `_api()` return type causes false LSP warnings

The common pattern `_api()` → `json.loads(resp.read())` returns `Any`, but
after error handling, the function always returns a `dict` (either the parsed
response or `{"error": ...}`). Pyright doesn't know this and flags every
`.get()` call on the result with `Cannot access attribute "get" for class "str"`.

**Fix:** These are safe at runtime — the `if "error" in data` guard ensures
you only proceed with dicts. To silence the linter, add a type assertion:

```python
data: dict = _api("GET", "/path")  # type: ignore[assignment]
```

Or ignore the warnings — they won't cause runtime errors.

### 8. GENERIC_SKILL.md must document all provider env vars

The "Adding a New Provider" section in the GENERIC_SKILL must list every
environment variable that each provider needs. If a user configures the MCP
bridge and only sets `ACCT_API_KEY` but the provider also needs `ACCT_SUBDOMAIN`,
they'll get a confusing auth error.

**Always update the GENERIC_SKILL.md when adding a new provider plugin**
that introduces new env vars.

---

## Quick Reference: Directory Tree

```
recipes/
├── accounting/                       # Finance: Bukku, QBO, Xero
│   ├── CONTRACT.md                   # 11 acct_* tools
│   ├── GENERIC_SKILL.md              # 10 workflows + 3 cron templates
│   ├── bridges/acct-bridge.py        # Unified bridge (plugin loader)
│   ├── plugins/
│   │   ├── bukku.py                  # Bukku REST API
│   │   ├── quickbooks.py             # QuickBooks Online API
│   │   └── xero.py                   # Xero API
│   ├── oauth-helper.py               # Shared OAuth2 module
│   └── providers/
│       ├── bukku.md
│       ├── quickbooks.md
│       └── xero.md
│
├── hr/time-tracking/                 # HR: Jibble, Kami
│   ├── CONTRACT.md                   # 9 tt_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/tt-bridge-jibble.py   # Per-provider bridge
│   └── providers/
│       ├── jibble.md
│       └── kami.md
│
├── procurement/                      # Procurement: PO, vendors, contracts
│   ├── CONTRACT.md                   # 6 proc_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/                      # Empty (ready for plugins)
│   ├── plugins/                      # Empty (ready for plugins)
│   └── providers/                    # Empty (ready for docs)
│
├── crm/                              # CRM: contacts, deals, pipeline
│   ├── CONTRACT.md                   # 7 crm_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/                      # Empty
│   ├── plugins/                      # Empty
│   └── providers/                    # Empty
│
├── marketing/                        # Marketing: campaigns, analytics
│   ├── CONTRACT.md                   # 5 mkt_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/                      # Empty
│   ├── plugins/                      # Empty
│   └── providers/                    # Empty
│
├── compliance/                       # Compliance: e-sign, policies
│   ├── CONTRACT.md                   # 5 comp_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/                      # Empty
│   ├── plugins/                      # Empty
│   └── providers/                    # Empty
│
├── support/                          # Support: tickets, SLAs
│   ├── CONTRACT.md                   # 5 spt_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/                      # Empty
│   ├── plugins/                      # Empty
│   └── providers/                    # Empty
│
├── engineering/                      # Engineering: repos, issues, CI
│   ├── CONTRACT.md                   # 6 eng_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/                      # Empty
│   ├── plugins/                      # Empty
│   └── providers/                    # Empty
│
├── projects/                         # Projects: tasks, milestones
│   ├── CONTRACT.md                   # 6 proj_* tools
│   ├── GENERIC_SKILL.md
│   ├── bridges/                      # Empty
│   ├── plugins/                      # Empty
│   └── providers/                    # Empty
│
└── product/                          # Product: ideas, roadmaps
    ├── CONTRACT.md                   # 5 pd_* tools
    ├── GENERIC_SKILL.md
    ├── bridges/                      # Empty
    ├── plugins/                      # Empty
    └── providers/                    # Empty
```
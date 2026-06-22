# Scrum Config Schema

Per-profile configuration file at `~/.hermes/profiles/<profile>/scrum.yaml`.

## Pitfall: Regex in YAML — Always Use Single Quotes

YAML double-quoted strings interpret escape sequences, and `\d` is NOT a valid YAML escape. This causes a parse error:

```yaml
# ❌ WRONG — YAML ScannerError: unknown escape character 'd'
task_id_patterns:
  - pattern: "TS-20\d{2}-\d{3}"

# ✅ CORRECT — single quotes pass the regex literally
task_id_patterns:
  - pattern: 'TS-20\d{2}-\d{3}'
```

**Rule:** Regex patterns in scrum.yaml MUST use single-quoted YAML strings. Double quotes break.

## Full Schema

```yaml
# ── Identity ──
profile: "project-manager"           # Profile slug (required)
app_name: "Gorobei"                  # Agent name for DM greetings (required)

# ── Slack Channels ──
channel_updates: "C09SR9B5WJU"      # Scrum summary channel (required)
channel_leadership: "C0B4792J3AP"   # Enriched 5pm report channel (optional, falls back to updates)

# ── State ──
state_dir: "~/.hermes/scrum-states/<profile>"  # State file dir

# ── Team Roster ──
team:
  - name: "Sheikh Syazwan"
    slack_id: "U060MSDBQMQ"
    role: "Head of Project"

# ── Brain Cross-Reference ──
brain:
  source: "projects"                 # gbrain source
  task_id_patterns:                  # SINGLE quotes for regex!
    - pattern: 'TS-20\d{2}-\d{3}'
      label: "Support Ticket"
      brain_path: "~/brain/projects/support_tickets/INDEX.md"
    - pattern: 'PRJ-\d{3}'
      label: "Project Task"
  domain_terms:
    - "Alam Flora"
    - "IOI"
  custom_ref:
    project_dir: "~/brain/projects/active_projects/"
    ticket_index: "~/brain/projects/support_tickets/INDEX.md"
```

## Per-Profile Examples

### Projects (Gorobei)

```yaml
profile: project-manager
app_name: Gorobei
channel_updates: "C09SR9B5WJU"
channel_leadership: "C0B4792J3AP"
brain:
  source: projects
  task_id_patterns:
    - pattern: 'TS-20\d{2}-\d{3}'
      label: "Support Ticket"
  domain_terms:
    - Alam Flora, Forestias, Kossan, Petronas, MRCSB, Vitrox, Vinda
    - Bank Tabungan, BTN, CC Fresh, Canon, Capitol, 1U
    - IOI, U Mobile, PaviKL, RPG, Casebang, Pandora
```

### Product (Shi)

```yaml
profile: product-manager
app_name: Shi
channel_updates: "C0308PA6Y"
channel_leadership: "C0ABY3VT4U8"
brain:
  source: products
  task_id_patterns:
    - pattern: 'SAM-\d{2}-\d{2}-\d{3,4}'
      label: "SAM Task"
    - pattern: 'INT-\d+'
      label: "Integration Task"
    - pattern: 'EP-\d+'
      label: "Epic"
  domain_terms:
    - SamurAI, V2 Lite, Karo, Shogun, Runner, Executor, City OS
    - ReID, VMS, Queue, Dashboard, GPU Inference
```

### HR (Jinzai)

```yaml
profile: hr-manager
app_name: Jinzai
channel_updates: "C08XXXXXXX"
brain:
  source: hr
  task_id_patterns:
    - pattern: 'HR-\d+'
      label: "HR Task"
  domain_terms:
    - leave, medical, MC, attendance, hiring, onboarding
    - interview, Jibble, timesheet, overtime
```

### Finance (Koku)

```yaml
profile: finance-manager
app_name: Koku
channel_updates: "C09XXXXXXX"
brain:
  source: finance
  task_id_patterns:
    - pattern: 'PO-\d+'
      label: "Purchase Order"
    - pattern: 'INV-\d+'
      label: "Invoice"
  domain_terms:
    - burn rate, P&L, budget, invoice, vendor, payment
    - audit, reconciliation, forecast
```

### CRM (Kizuna)

```yaml
profile: crm-manager
app_name: Kizuna
channel_updates: "C0AXXXXXXX"
brain:
  source: crm
  domain_terms:
    - deal, pipeline, demo, proposal, proposal sent
    - negotiation, closing, follow-up
```

### Support (Bōei)

```yaml
profile: customer-support
app_name: Bōei
channel_updates: "C0BXXXXXXX"
brain:
  source: support
  task_id_patterns:
    - pattern: 'TS-20\d{2}-\d{3}'
      label: "Support Ticket"
  domain_terms:
    - escalation, SLA, resolution, ticket
    - severity, client, follow-up
```
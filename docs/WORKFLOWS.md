# Workflows — Shogun OS

This document details the core runtime flows of Shogun OS using Mermaid sequence diagrams.

---

## Workflow 1: Weekly Executive Financial Pulse Report

**Trigger:** Scheduled cron (`0 8 * * 1`) or manual command (`/weekly-pulse-report` / `hermes -p finance-manager -z "/weekly-pulse-report"`).  
**Actor:** Koku (`finance-manager` profile agent).

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Cron
    participant Koku as Koku (finance-manager)
    participant Script as weekly_pulse.py
    participant MCP as acct_* Provider Bridge
    participant GBrain as GBrain (finance/ source)

    User->>Koku: Execute /weekly-pulse-report
    Koku->>Script: Run weekly_pulse.py (or execute acct_* tools)
    
    Script->>MCP: acct_get_balance_sheet(as_of_date=today)
    MCP-->>Script: Return bank balances & cash position
    
    Script->>MCP: acct_get_aging_report(type="receivable")
    MCP-->>Script: Return AR aging buckets (0-30, 31-60, 61-90, 90+)
    
    Script->>MCP: acct_get_aging_report(type="payable") & acct_list_purchase_bills()
    MCP-->>Script: Return AP commitments due this week
    
    Script->>MCP: acct_get_profit_loss(date_from=month_start, date_to=today)
    MCP-->>Script: Return MTD revenue & spend pacing
    
    Script->>Script: Compute net burn rate & cash runway months
    Script-->>Koku: Formatted Executive Markdown Pulse Report
    
    Koku->>GBrain: Save report to finance/reports/weekly/YYYY-MM-DD.md
    Koku-->>User: Deliver executive report to Slack / Telegram channel
```

### Edge Cases & Failure Modes
- **Missing Provider Credentials:** If live `acct_*` tools are unavailable, `weekly_pulse.py` falls back to `--dry-run` sample data and notes the fallback state in the output header.
- **API Rate Limits / Outage:** The script catches HTTP connection errors gracefully and reports last cached figures with a staleness warning (`⚠️ Data as of cached timestamp`).

---

## Workflow 2: Monthly Board Report & BvA Variance Analysis

**Trigger:** Scheduled cron (`0 8 1 * *`) or manual command (`/monthly-board-report`).  
**Actor:** Koku (`finance-manager` profile agent).

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Cron
    participant Koku as Koku (finance-manager)
    participant BoardScript as monthly_board.py
    participant VarScript as variance.py
    participant MCP as acct_* Provider Bridge
    participant GBrain as GBrain Store

    User->>Koku: Execute /monthly-board-report
    Koku->>BoardScript: Run monthly_board.py
    
    BoardScript->>MCP: Pull P&L, Balance Sheet & Customer Invoices
    MCP-->>BoardScript: Return P&L JSON + Balance Sheet + Invoice lines
    
    BoardScript->>VarScript: Invoke subprocess: variance.py --budget budget.json --actuals P&L
    VarScript->>VarScript: Compute variances per account code
    VarScript->>VarScript: Flag >10% overruns (⚠️ OVERRUN)
    VarScript-->>BoardScript: Return JSON variance breakdown & alerts
    
    BoardScript->>BoardScript: Compute customer revenue concentration (>20% single client risk)
    BoardScript-->>Koku: Formatted 5-Section Board Report Markdown
    
    Koku->>GBrain: Archive to finance/reports/monthly/YYYY-MM.md
    Koku-->>User: Deliver to Executive Board channel / Telegram
```

### Edge Cases & Failure Modes
- **Missing `budget.json`:** If `budget.json` baseline does not exist in the profile folder, `variance.py` returns actual figures with a warning: `⚠️ Budget baseline (budget.json) missing. Showing actuals only.`
- **Unicode Console Encoding on Windows:** `monthly_board.py` explicitly forces `sys.stdout` UTF-8 wrapper and sets `PYTHONIOENCODING=utf-8` on subprocess execution to prevent `cp1252` character encoding failures on emojis.

---

## Workflow 3: 3-Tier Department Scrum Standup

**Trigger:** Cron jobs (Morning 9:00 AM, Midday 11:00 AM, EOD 5:00 PM weekdays).  
**Actor:** Department Manager Agent (e.g. `finance-manager` Koku).

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Hermes Cron Service
    participant Agent as Department Agent (Koku)
    participant Team as Team Members (Slack / Telegram)
    participant Channel as Team Channel

    Note over Cron, Channel: Tier 1: Morning Standup (9:00 AM)
    Cron->>Agent: Trigger morning standup
    Agent->>Agent: Read scrum.yaml config
    loop For each team member
        Agent->>Team: Send DM: "What are your top priorities today?"
    end

    Note over Cron, Channel: Tier 2: Midday Check-in (11:00 AM)
    Cron->>Agent: Trigger midday check-in
    Agent->>Agent: Audit missing replies from morning standup
    loop For non-responders
        Agent->>Team: Send DM reminder: "Please submit your standup update."
    end

    Note over Cron, Channel: Tier 3: EOD Summary (5:00 PM)
    Cron->>Agent: Trigger EOD summary
    Agent->>Agent: Compile all responses, completed tasks & blockers
    Agent->>Channel: Post formatted EOD Scrum Wrap-up summary
```

---

## Workflow 4: Profile Provisioning & Cron Wiring

**Trigger:** CLI deployment command (`generate-profile.py` & `wire-crons.py`).  
**Actor:** System Administrator / Deployment Agent.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin / Deployer
    participant Gen as generate-profile.py
    participant Wire as wire-crons.py
    participant Hermes as Hermes Profile Store (~/.hermes/profiles/)

    Admin->>Gen: python3 scripts/generate-profile.py finance-manager --type finance --force
    Gen->>Hermes: Create config.yaml & SOUL.md
    Gen->>Hermes: Copy scrum.yaml template from examples/scrum-configs/
    Gen->>Hermes: Seed initial budget.json baseline template
    Gen->>Hermes: Link/copy all 22 finance skills into skills/
    Gen-->>Admin: Profile finance-manager generated successfully

    Admin->>Wire: python3 scripts/wire-crons.py finance-manager --type finance --apply
    Wire->>Hermes: Register 4 scrum crons + 4 domain crons into Hermes DB
    Wire-->>Admin: 8 cron jobs applied successfully
```

---

## Workflow 5: Executive & Operations Web Portal Finance Dashboard

**Trigger:** User clicks on the **Finance Department Dashboard** in the Shogun OS Web Portal (`http://localhost:5173`).  
**Actor:** Web Portal User / Executive / Finance Staff.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Executive
    participant UI as FinanceDashboard.tsx (React UI)
    participant API as departmentsApi (api.ts)
    participant Server as FastAPI Server (:8000)
    participant GBrain as GBrain Store (finance/)
    participant Mock as examples/finance-budget.json

    User->>UI: Select Finance Department -> Dashboard Tab
    UI->>API: dashboardFinanceStats("finance")
    API->>Server: GET /api/departments/finance/dashboard/finance-stats
    
    Server->>GBrain: gbrain_fetch_pages("finance", limit=300)
    
    alt GBrain Snapshots Found
        GBrain-->>Server: Return snapshot pages (cash, PL, AR, AP, BvA, compliance)
        Server->>Server: Run _run_finance_aggregation() on live snapshots
    else GBrain Snapshots Empty / New Tenant
        Server->>Mock: Read fallback mock dataset from examples/finance-budget.json
        Mock-->>Server: Return Malaysian entities + English terms dataset
    end

    Server-->>API: Return FinanceDashboardStats JSON (All 5 Tabs)
    API-->>UI: Update React Query state (refetchInterval: 120s)

    alt Active Tab == "pulse"
        UI->>UI: Render ExecutivePulseTab (KPI Cards, Risk Alert Banners, ComboChart)
    else Active Tab == "runway"
        UI->>UI: Render CashRunwayTab (Runway Dial, Bank Accounts, 13-Wk Forecast, FX)
    else Active Tab == "ops"
        UI->>UI: Render WorkingCapitalOpsTab (AR Aging, Dunning Queue, AP 3-Way Match)
    else Active Tab == "bva"
        UI->>UI: Render BvaUnitEconomicsTab (Dept BvA Chart, Variance Table, Unit Econ)
    else Active Tab == "compliance"
        UI->>UI: Render CloseTaxComplianceTab (Checklist, MY Statutory, SST-02, CP58, WHT)
    end
```

### Edge Cases & Failure Modes
- **GBrain Service Offline:** If the GBrain daemon or PostgreSQL connection fails, `_run_finance_aggregation()` catches the connection error and seamlessly falls back to reading `examples/finance-budget.json` so the UI remains fully functional.
- **New Tenant Zero-State:** For fresh tenants with no transaction history, `examples/finance-budget.json` provides populated Malaysian demo data for immediate executive evaluation.

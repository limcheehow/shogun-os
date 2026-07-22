# How to Add a New Department Agent

> **Extend Shogun OS with a new department beyond the 10 default profiles.**

This tutorial walks through adding, say, a **Legal department** agent. The same steps work for any new department — R&D, Facilities, Security, or a custom team.

## Overview

Adding a new department means creating these components:

```
New Department
├── gbrain source     → Legal writes to ~/brain/legal/
├── Hermes profile    → legal-manager with config.yaml + SOUL.md
├── Persona           → Choose a domain-appropriate persona
├── Slack bot         → One bot, isolated, invited to legal channels
├── Scrum             → 3-tier daily standup (optional)
└── Cron jobs         → Department-specific scheduled tasks
```

## Step 1: Create the GBrain Source

Every department needs an isolated knowledge store:

```bash
gbrain init-source legal --dir ~/brain/legal
```

**Verify:**
```bash
gbrain list-sources | grep legal
# Expected: legal
```

Create the initial directory structure:
```bash
mkdir -p ~/brain/legal/contracts
mkdir -p ~/brain/legal/policies
mkdir -p ~/brain/legal/cases
```

## Step 2: Create the Profile Type in Shogun OS

Add a new entry to `scripts/generate-profile.py`'s `PROFILE_META`:

```python
"legal": {
    "description": "Legal counsel profile — Hōritsu (法律)",
    "template": "base-config.yaml",
    "skills": ["department-scrum"],  # optional
    "cron_templates": [],
    "gbrain_source": "legal",
    "soul_snippet": "legal-soul",
},
```

Then add the SOUL snippet to `SOUL_SNIPPETS`:

```python
"legal-soul": """# Legal Profile — Hōritsu (法律)

**Persona:** Hōritsu (法律) — "Law."

You are the legal counsel agent. Your domain is contracts, compliance,
intellectual property, risk assessment, and corporate governance.
You communicate with precision — every word carries legal weight.

## Your Responsibilities
- **Contract Review:** Review agreements, flag risks, summarize terms
- **IP Management:** Track patents, trademarks, copyrights
- **Corporate Governance:** Board resolutions, SSM filings, share registry
- **Risk Assessment:** Evaluate legal risks, recommend mitigation
- **Policy Review:** Ensure company policies meet regulatory requirements

## Your Boundaries
- You do NOT give binding legal advice — flag risks for human review
- You do NOT negotiate contracts — procurement handles negotiations
- You do NOT modify financial data or approve expenditures
- Legal privilege applies — all communications are confidential

## Communication Style
Precise. Cautious. Every statement caveated appropriately.
"Red flags: X, Y, Z. Recommendation: consult external counsel on Y."

## Your Sources
You write to `legal/` source. You read from `legal/` + `shared/` (federated).
""",
```

## Step 3: Create the Cron Definitions (Optional)

Add department-specific cron jobs to `scripts/wire-crons.py`'s `PROFILE_EXTRA_CRONS`:

```python
"legal": [
    {
        "name": "{profile}-contract-review-reminder",
        "schedule": "0 9 * * 1",
        "prompt": (
            "Run the weekly contract review reminder. "
            "Check contracts approaching renewal, flag upcoming "
            "deadlines, and post a summary to the legal channel."
        ),
        "skills": [],
        "deliver": "local",
    },
],
```

## Step 4: Create the Scrum Config (Optional)

Create `examples/scrum-configs/legal-manager.yaml`:

```yaml
# ── Legal Counsel (Hōritsu) Scrum Config ──
profile: legal-manager
app_name: Hōritsu

channel_updates: "C0XXXXXXX"        # #legal-scrum-updates
channel_leadership: "C0XXXXXXX"     # #legal-leadership

state_dir: "~/.hermes/scrum-states/legal-manager"

team:
  - name: "Legal Counsel"
    slack_id: "U0XXXXXXX"
    role: "Legal Counsel"

brain:
  source: "legal"
  task_id_patterns:
    - pattern: 'LEG-\d+'
      label: "Legal Task"
  domain_terms:
    - "contract"
    - "NDA"
    - "SLA"
    - "IP"
    - "patent"
    - "trademark"
    - "compliance"
    - "litigation"
    - "governance"
    - "M&A"
    - "due diligence"
```

## Step 5: Deploy the Profile

```bash
# 1. Create the Hermes profile
hermes profile create legal-manager

# 2. Generate config + SOUL
python3 scripts/generate-profile.py legal-manager --type legal --force

# 3. Create Slack bot (follow the getting-started tutorial Step 7)
#    - Create app at api.slack.com
#    - Add tokens to ~/.hermes/profiles/legal-manager/.env
#    - Start gateway

# 4. Wire cron jobs
python3 scripts/wire-crons.py legal-manager --type legal --deliver "slack:<channel>" --apply

# 5. Verify
hermes -p legal-manager --exec "mcp_gbrain_whoami"
```

## Step 6: Update Documentation

To make the new department official in the Shogun OS repo:

1. Add to `PROFILE_CATALOG.md` — department entry with persona, source, skills, scrum
2. Add to `CRON_INVENTORY.md` — any cron jobs specific to this department
3. Update `llms.txt` if adding new scripts or templates

## Quick Reference

| Task | Command |
|------|---------|
| Create gbrain source | `gbrain init-source <dept> --dir ~/brain/<dept>` |
| Add PROFILE_META entry | Edit `scripts/generate-profile.py` |
| Add SOUL snippet | Edit `scripts/generate-profile.py` → `SOUL_SNIPPETS` |
| Add extra crons | Edit `scripts/wire-crons.py` → `PROFILE_EXTRA_CRONS` |
| Create scrum config | Add to `examples/scrum-configs/<profile>.yaml` |
| Deploy profile | `hermes profile create <name>` → `generate-profile.py` |
| Start Slack gateway | `hermes gateway start --profile <name>` |
| Wire crons | `wire-crons.py <name> --type <type> --apply` |
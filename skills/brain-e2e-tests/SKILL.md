---
name: brain-e2e-tests
description: "Comprehensive E2E test suite for brain compliance, timeline, cron validation, and HR migration. Run after any brain infrastructure change."
version: 1.0.0
author: Your Company
tags: [brain, gbrain, testing, compliance, e2e]
---

# Brain E2E Tests

Run after any brain infrastructure change (validator, cron wiring, HR migration, timeline injection).

## Test Coverage

| Section | Checks | What it tests |
|---------|--------|---------------|
| Validator | 6 | compliant pages pass, bare wikilinks caught, missing title, type: format |
| Pre-Commit Hook | 4 | hook exists, executable, references validator, has escape hatch |
| Timeline | 2 | gbrain timeline command, entries present |
| Cron Config | 5 | all brain-writing crons have brain-compliance skill loaded |
| Script Validation | 6 | all 3 script-only crons have validator inline |
| HR Migration | 3 | HR/ gone, hr/ exists, KPI files pass |

## Run

```bash
python3 ~/.hermes/skills/gbrain/brain-e2e-tests/SKILL.md
```

Or from the standalone script:
```bash
python3 /tmp/brain-e2e-tests.py
```

## Expected Results

```
22 passed, 0 failed
```

## When to Run

- After modifying `validate-brain-page.py`
- After wiring new cron jobs that write brain pages
- After any folder migration (HR/ → hr/, people/ → persons/, etc.)
- After timeline injection campaigns
- After updating the pre-commit hook
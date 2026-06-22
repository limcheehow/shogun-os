# Test Suite Reference

Cross-department scrum test suite at:

```
~/.hermes/scripts/scrum/test-scrum-cross-dept.py
```

Run: `python3 ~/.hermes/scripts/scrum/test-scrum-cross-dept.py`

## What It Covers (48 tests)

| Section | Tests | What |
|---|---|---|
| 1. Config Parsing | 4 | Projects, Products, HR, Finance — 5 required fields |
| 2. Task ID Extraction | 7 | All dept regex patterns on real-world reply text |
| 3. Domain Term Matching | 6 | Department-specific keywords found/not-found |
| 4. Quality (SMART Gates) | 8 | HIGH/MEDIUM/LOW classification; "Blockers: none" false positive guard |
| 5. State File Schema | 4 | 14 member fields, 7 top-level fields, JSON round-trip |
| 6. Script Help & Rejection | 4 | --help works, --profile is required |
| 7. Config Validity | 8 | Checks real profile directories |
| 8. Edge Cases | 6 | Empty/minimal replies, cross-dept isolation, empty patterns |

## Run Before Deploying a New Department

When adding scrum.yaml for a new department:
1. Create the scrum.yaml
2. Add test cases in test-scrum-cross-dept.py (new SAMPLE_ config, task ID tests, term tests)
3. Run `python3 test-scrum-cross-dept.py` — all 48+ tests must pass
4. Deploy crons
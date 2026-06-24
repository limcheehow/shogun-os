# Cron-to-Compliance Workflow

How cron jobs that write brain pages integrate with the Gbrain compliance gate.

## Principle

Every cron job that creates or modifies a brain file must:

1. Write the file with correct frontmatter for its entity type
2. Run `validate-brain-page.py` on the file
3. Fix any violations before delivering the result

## Currently Patched Cron Jobs

These cron jobs already have a compliance validation step:

| Cron Job | Writes To | Validation Step |
|----------|-----------|-----------------|
| End of Day Summary | `daily/YYYY-MM-DD.md` | Step 3: Validate Compliance |
| Morning Briefing | `daily/briefings/YYYY/MM/YYYY-MM-DD.md` | Step 5: Validate Compliance |
| Weekly Brain Health Audit | Full batch scan | Runs `validate-brain-page.py ~/brain/ --batch --json` |

## Cron Jobs That Write to Brain via Skills (Indirect Coverage)

These cron jobs don't write brain pages directly — they use the `profile-enrichment` skill which now has its own compliance validation built in:

| Cron Job | How It Writes | Coverage |
|----------|--------------|----------|
| Daily Email Digest | Calls profile-enrichment for new contacts | ✅ Protected (skill has validation) |
| calendar-daily-sync | Calls profile-enrichment for unknown attendees | ✅ Protected |
| Meeting-Agent Sync | Calls profile-enrichment for meeting attendees | ✅ Protected |

## Pattern for Adding Validation to a New Cron Job

Add this step after any brain write step in the cron prompt:

```markdown
### Final Step: Validate Compliance
Run the compliance check on the written file:
```bash
python3 ~/.hermes/skills/productivity/brain-folder-organization/scripts/validate-brain-page.py ~/brain/path/to/file.md
```
If any violations are reported, fix them before delivering.
```

## Verification

To verify a cron job's compliance integration after patching:

```bash
# Check the cron prompt contains the validation command
grep -n "validate-brain-page" ~/.hermes/cron/jobs.json | grep <job-name>
```

## Skills That Have Compliance Patching

| Skill | Files Validated | Location of Step |
|-------|----------------|------------------|
| profile-enrichment | persons/, companies/ | Step 5: Validate Compliance (MANDATORY) |
| sales-enquiry-processing | persons/, companies/, deals/ | Validate Compliance section |
| brain-folder-organization | All (gate keeper) | ⚠️ Gbrain Compliance Gate section |

## Enforcement Path

When a cron job or skill creates a brain page without validation:

1. The weekly brain health audit (Sunday 9AM) will catch it via batch scan
2. The file will show up as non-compliant in the per-folder breakdown
3. The Sunday report flags it for attention

The goal is to catch violations at write time (before delivery), but the weekly audit provides a safety net.
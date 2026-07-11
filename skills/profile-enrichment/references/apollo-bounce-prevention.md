# Apollo Bounce Prevention — Real Examples

This file documents real bounce incidents and their root causes. Each entry is a lesson in what to check before sending.

## Incident 1: Bonia IT Team — Wrong Domain (Jun 2, 2026)

**What happened**: Shinny Tan and Sze Yee Tan's emails bounced.

**What was used**: `shinny_tan@bonia.com`, `sze_yee_tan@bonia.com`

**What Apollo returned**: `shinny.tan@boniacorp.com` (verified) — note DIFFERENT domain @boniacorp.com not @bonia.com, and DIFFERENT format (first.last not first_last)

**Root cause**: 
1. Subagent processed the Apollo result and saved the email as `shinny_tan@bonia.com` — it applied the `first_last@bonia.com` pattern to the name without checking the actual returned email string.
2. The `domain` parameter used for lookup was `bonia.com`, but Apollo's database returned an email from a different domain `boniacorp.com`. The code that parsed the result overrode the returned email with the guessed pattern.

**Lesson**: NEVER trust an inferred pattern over Apollo's actual returned email. If Apollo returns `shinny.tan@boniacorp.com`, USE THAT EXACT STRING. The queried domain (bonia.com) is just a search parameter — the result may come from a different domain entirely.

**Fix**: Profiles updated to `shinny.tan@boniacorp.com` (verified) and `sze.yee.tan@boniacorp.com` (estimated from team pattern). Draft re-saved.

## Incident 2: Lotus's — Wrong Domain (Jun 2, 2026)

**What was used**: `john.chan@lotuss.com.my`, `samuel.lee@lotuss.com.my`

**What Apollo returned**: `john.chan@lotuss.com` (verified), `samuel.lee@lotuss.com` (verified)

**Root cause**: Assumed `.my` TLD based on "Malaysia" operation. Apollo confirmed the primary domain is `@lotuss.com` without country TLD.

**Lesson**: For regional subsidiaries, the corporate email domain may differ from the local website domain (lotuss.com.my vs lotuss.com). Always verify the mail domain separately.

## Prevention Checklist

Before drafting ANY sales email, run this verify pass:

1. `people/match` for EACH contact with their company domain
2. Write down the EXACT email string returned (both local part AND domain)
3. If Apollo returns `(verified)`, trust the email string literally — don't reformat it
4. If Apollo returns nothing, check NeverBounce/RocketReach for aggregated patterns
5. Flag all unmatchable contacts as "estimated" in the draft with a warning
6. Only after all checks, compose the email

## Multi-Company Domain Patterns (from experience)

| Company | Primary Domain | Secondary Domain | Notes |
|---------|---------------|-----------------|-------|
| Bonia | @bonia.com | @boniacorp.com | IT team uses @boniacorp.com |
| Lotus's | @lotuss.com | @lotuss.com.my | .my is customer-facing only |
| Parkson | @parkson.com.my | — | Mixed first@ and firstlast@ formats |

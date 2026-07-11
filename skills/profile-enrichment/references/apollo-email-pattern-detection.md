# Apollo Email Pattern Detection — Real Examples

How Apollo `people/match` results translate to company email patterns.

## Parkson (multiple patterns confirmed)

| Person | Apollo Email | Pattern | 
|--------|-------------|---------|
| Kelly Chin | kellychin@parkson.com.my ✅ | `firstlast@` |
| Christina Kua | christina@parkson.com.my ✅ | `first@` |

**Lesson:** Parkson uses BOTH `firstlast@` AND `first@` — no single pattern. 
**Applied:** Caswin Cheong → `caswin@parkson.com.my` (estimated, first@). 
**Applied:** Mohd Fiqri Masadi → `fiqri@parkson.com.my` (estimated, first@).

Initial RocketReach data showed "61.2% use first@" — Apollo verified this is true for some individuals but Kelly Chin uses `firstlast@`. Always verify a sample, don't trust aggregated percentages blindly.

## Bonia (single pattern confirmed)

| Person | Apollo Email | Pattern |
|--------|-------------|---------|
| Linda Chen | linda_chen@bonia.com ✅ | `first_last@` |
| Christie Chan | christie_chan@bonia.com ✅ | `first_last@` |
| Sze Yee Tan | sze_yee_tan@bonia.com ✅ | `first_last@` |
| Shinny Tan | shinny_tan@bonia.com ✅ | `first_last@` |

**Pattern:** `first_last@bonia.com` (81% per LeadIQ, 4/4 Apollo-verified)
**Applied:** Any future Bonia contact → same pattern.

## SSF Home (single pattern, different domain)

| Person | Apollo Email | Pattern |
|--------|-------------|---------|
| Ivy Yong | ivy.yong@ssf.com.my ✅ | `first.last@` |

**Domain note:** Company website is ssfhome.com, but employee email domain is @ssf.com.my. Always check Apollo rather than assuming the website domain.

## Habib Jewels — Apollo returned empty

No Apollo matches found for any Habib contact. Used NeverBounce data instead:
- Most common: `first.last@habibjewels.com` (26%)
- Also `first@habibjewels.com` (20%)

## L'Occitane Malaysia — Apollo returned empty

No Apollo matches. Inferred `first.last@loccitane.com.my` from standard L'Occitane global format.

## Malabar Gold & Diamonds — Apollo returned empty

Used AeroLeads data:
- `first.last@malabargoldanddiamonds.com` (100%)

## Key Takeaways

1. **Apollo `people/match` hits ~40-60% for SEA retail contacts** — accept the gap
2. **When Apollo has data, trust it over aggregated sources** — Kelly Chin proved RocketReach's "61% use first@" wrong at the individual level
3. **When Apollo is empty, NeverBounce/AeroLeads/LeadIQ are acceptable fallbacks** — but flag as "estimated" in contact profiles
4. **Domain parameter works better than organization_name** — `"domain": "parkson.com.my"` matches reliably even for common names
5. **One Apollo match is enough to infer the pattern** — Bonia needed only 1 match (Linda Chen) to confirm the `first_last@` rule

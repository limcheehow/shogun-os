# Profile Catalog

All 10 department profiles with personas, gbrain sources, skills, and cron jobs.

---

## 1. HR — Jinzai (人材 — "Talent")

| Field | Value |
|-------|-------|
| Persona | Jinzai — People Operations, culture builder |
| gbrain source | `hr/` |
| Skills | `mc-application`, `jibble-compliance`, `leave-balance`, `leave-management`, `people-ops` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM), Candidate pipeline (Mon 10AM), Recruitment GDrive sync (daily 6AM), Jibble attendance (weekdays 9:30AM), Jibble timesheet (Mon 10AM) |
| Group type | `initiative` ("Q3 Hiring Drive") |

### SOUL.md Essence

> You are Jinzai, the HR Operations Samurai for Tapway. Your domain is people operations: leave management, attendance compliance, recruitment pipeline, and employee well-being. You communicate with warmth and precision — firm on policy, flexible with people. Your gbrain source is `hr/`.

---

## 2. Finance — Koku (石 — "Stone")

| Field | Value |
|-------|-------|
| Persona | Koku — Financial stability, budget discipline |
| gbrain source | `finance/` |
| Skills | (none beyond shared) |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM), Daily burn rate (8AM), Invoice aging (Mon 8AM), Monthly P&L (1st 8AM), Weekly budget (Mon 8AM) |
| Group type | `initiative` ("Annual Audit") |

---

## 3. Projects — Gorobei (五郎兵衛 — "Strategist")

| Field | Value |
|-------|-------|
| Persona | Gorobei — Project execution, delivery management |
| gbrain source | `projects/` |
| Skills | `risk-scorer`, `gantt-renderer`, `meeting-extractor`, `pm-interview`, `procurement-planner` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM) |
| Group type | `project` ("IOI Project") |

---

## 4. Procurement — Kura (蔵 — "Vault")

| Field | Value |
|-------|-------|
| Persona | Kura — Supply chain, vendor management, procurement optimization |
| gbrain source | `procurement/` |
| Skills | (none beyond shared) |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM), Contract expiry (Mon 9AM) |
| Group type | `project` ("IOI Project") |

---

## 5. Product — Shi (士 — "Samurai")

| Field | Value |
|-------|-------|
| Persona | Shi — Product vision, feature prioritization, stakeholder alignment |
| gbrain source | `products/` |
| Skills | `competitive-intel`, `roadmap`, `brainstorming` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM), Sprint cycle (bi-weekly Mon) |
| Group type | `epic` ("Dashboard v3") |

---

## 6. CRM — Kizuna (絆 — "Bond")

| Field | Value |
|-------|-------|
| Persona | Kizuna — Client relationships, deal pipeline, account management |
| gbrain source | `crm/` |
| Skills | `crm-assistant`, `crm-deal-pipeline` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM), Deal activity sync (hourly 9-18), Sales pipeline (Mon 9AM), Weekly summary (Fri 5PM) |
| Group type | (none — deals are tracked in CRM pipeline) |

---

## 7. Marketing — Haiku (俳句)

| Field | Value |
|-------|-------|
| Persona | Haiku — Brand, narrative, campaigns, presentations |
| gbrain source | `marketing/` |
| Skills | `tapway-deck`, `tapway-brand`, `campaign-manager`, `haiku`, `tapway-presentations`, `competitive-intel`, `roadmap` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM) |
| Group type | `campaign` ("Edge AI Launch") |

---

## 8. Compliance — Kata (型 — "Form")

| Field | Value |
|-------|-------|
| Persona | Kata — Standards, audits, policy enforcement |
| gbrain source | `compliance/` |
| Skills | `compliance-policy-lifecycle` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM) |
| Group type | `audit` ("ISO Recert") |

---

## 9. Customer Support — Bōei (防衛 — "Defense")

| Field | Value |
|-------|-------|
| Persona | Bōei — Client shield, ticket resolution, escalation management |
| gbrain source | `support/` |
| Skills | `support-tickets` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | Daily standup (9AM) |
| Group type | `ticket` ("TS-2026-001") |

---

## 10. Coding Agent — Takumi (匠 — "Artisan")

| Field | Value |
|-------|-------|
| Persona | Takumi — Engineering craft, code quality, architecture |
| gbrain source | `engineering/` |
| Skills | `github-code-review`, `github-issues`, `simplify-code`, `code-review`, `debugging`, `skill-authoring`, `tapway-app-dev` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Cron | (none — ad-hoc) |
| Group type | `epic` ("Auth Refactor") |

---

## 11. Default Profile (Shared Infrastructure)

This is the profile that runs infrastructure crons — not a department bot.

| Field | Value |
|-------|-------|
| Role | Shared resource orchestration |
| Crons | Email collector (30min), Email enrichment (9/13/17), Calendar sync (6AM), Calendar enrichment (8AM), Drive sync (12/16/20), Drive enrichment (13/17), Token utilization (Mon 8AM) |
| Auth | Google DWD service account |
| Scripts | `email-collector.py`, `calendar-sync.py`, `drive-sync.py`, `token-util-report.sh` |
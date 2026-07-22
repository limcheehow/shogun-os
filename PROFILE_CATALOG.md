# Profile Catalog

Shogun OS profiles are organized by **industry vertical**. All companies get the **shared profiles** (HR, Finance, CRM, etc.), then pick an industry for department-specific agents.

---

## Shared Profiles (Every Industry)

These 8 department profiles + default infrastructure + executive assistant are deployed for **every** company regardless of industry.

| # | Profile | Persona | Kanji | Role |
|---|---------|---------|-------|------|
| 1 | HR | Jinzai | 人材 — "Talent" | People operations, leave, recruitment |
| 2 | Finance | Koku | 石 — "Stone" | Budget, cost, financial reporting |
| 3 | Procurement | Kura | 蔵 — "Vault" | Supply chain, vendor management |
| 4 | CRM | Kizuna | 絆 — "Bond" | Client relationships, deal pipeline |
| 5 | Marketing | Haiku | 俳句 | Brand, campaigns, content |
| 6 | Compliance | Kata | 型 — "Form" | Standards, audits, policy |
| 7 | Customer Support | Boei | 防衛 — "Defense" | Tickets, SLAs, escalation |
| 8 | Coding | Takumi | 匠 — "Artisan" | Engineering, code quality |
| — | Default | — | — | Shared infrastructure crons |
| — | Executive | Benkei | 弁慶 | CEO scheduling, travel, correspondence |

---

## General Industry (Services, Consulting, Software)

These profiles handle project delivery and product management — the core of services companies.

### Projects — Gorobei (五郎兵衛 — "Strategist")

| Field | Value |
|-------|-------|
| Persona | Gorobei — Project execution, delivery management |
| gbrain source | `projects/` |
| Skills | `risk-scorer`, `gantt-renderer`, `meeting-extractor`, `pm-interview`, `procurement-planner` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` included as example |
| Extra Crons | (none — scrum-only) |
| Task IDs | `TS-20\\d{2}-\\d{3}` |

### Product — Shi (志 — "Will")

| Field | Value |
|-------|-------|
| Persona | Shi — Product vision, feature prioritization, stakeholder alignment |
| gbrain source | `products/` |
| Skills | `competitive-intel`, `roadmap`, `brainstorming` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Sprint cycle (bi-weekly Mon) |
| Task IDs | `SAM-\\d{2}-\\d{2}-\\d{3,4}`, `INT-\\d+`, `EP-\\d+` |

---

## Manufacturing Industry (Factory, Production, OEM)

These profiles handle factory floor operations, quality control, maintenance, warehouse, and HSE — the core of manufacturing companies.

### Production — Kojo (工場 — "Factory")

| Field | Value |
|-------|-------|
| Persona | Kojo — Factory floor operations, OEE, work orders |
| gbrain source | `production/` |
| Skills | `production-oee`, `work-order-tracking`, `erp-connector`, `mes-connector` |
| Shared | `department-scrum`, `company-workflow`, `brain-compliance`, `slack-formatting` |
| Scrum | ✅ 3-tier |
| Extra Crons | Daily production schedule (6AM), OEE tracking (hourly) |

### Quality — Kensa (検査 — "Inspection")

| Field | Value |
|-------|-------|
| Persona | Kensa — QC inspections, NCRs, CAPA, lot traceability |
| gbrain source | `quality/` |
| Skills | `quality-ncr`, `quality-capa`, `erp-connector` |
| Shared | `department-scrum`, `company-workflow`, `brain-compliance`, `slack-formatting` |
| Scrum | ✅ 3-tier |
| Extra Crons | Inspection dashboard (7AM) |

### Maintenance — Shuri (修理 — "Repair")

| Field | Value |
|-------|-------|
| Persona | Shuri — PM, breakdowns, spare parts, MTBF/MTTR |
| gbrain source | `maintenance/` |
| Skills | `maintenance-pm`, `maintenance-downtime`, `mes-connector` |
| Shared | `department-scrum`, `company-workflow`, `brain-compliance`, `slack-formatting` |
| Scrum | ✅ 3-tier |
| Extra Crons | PM schedule (6AM) |

### Warehouse — Soko (倉庫 — "Storehouse")

| Field | Value |
|-------|-------|
| Persona | Soko — Inventory, shipping, cycle counts |
| gbrain source | `warehouse/` |
| Skills | `warehouse-inventory`, `erp-connector` |
| Shared | `company-workflow`, `brain-compliance`, `slack-formatting` |
| Scrum | ❌ (on-demand) |
| Extra Crons | Inventory status (6AM) |

### HSE — Anzen (安全 — "Safety")

| Field | Value |
|-------|-------|
| Persona | Anzen — Safety, incidents, permits, environmental monitoring |
| gbrain source | `hse/` |
| Skills | `hse-incident` |
| Shared | `company-workflow`, `brain-compliance`, `slack-formatting` |
| Scrum | ❌ (on-demand) |
| Extra Crons | Safety walk schedule (weekly Mon) |

---

## Retail Industry (Stores, E-commerce, Omnichannel)

These profiles handle stores, merchandising, e-commerce, CRM/loyalty, supply chain, and visual merchandising.

### Stores — Tenpo (店舗 — "Shop")

| Field | Value |
|-------|-------|
| Persona | Tenpo — Store operations, daily sales, customer experience |
| gbrain source | `stores/` |
| Skills | `store-sales-dashboard`, `store-staff-scheduling`, `store-replenishment` |
| Shared | `department-scrum`, `company-workflow`, `brain-compliance`, `slack-formatting` |
| Scrum | ✅ 3-tier |
| Extra Crons | Daily sales report (6AM), staff scheduling (Mon 8AM) |

### Merchandising — Shohin (商品 — "Goods")

| Field | Value |
|-------|-------|
| Persona | Shohin — Buying, assortment, vendor negotiation, pricing |
| gbrain source | `merchandising/` |
| Skills | `assortment-planning`, `vendor-negotiation`, `promo-planning` |
| Shared | `company-workflow`, `brain-compliance`, `slack-formatting` |
| Extra Crons | Slow-movers report (Mon 6AM), vendor contract expiry (Mon 9AM) |

### E-commerce — Denshi (電子 — "Digital")

| Field | Value |
|-------|-------|
| Persona | Denshi — Online store, Shopee/Lazada, listings, orders |
| gbrain source | `ecommerce/` |
| Skills | `ecommerce-listing`, `ecommerce-order-management`, `marketplace-analytics` |
| Shared | `company-workflow`, `brain-compliance`, `slack-formatting` |
| Extra Crons | New orders check (hourly 9-18), listing compliance (7AM) |

### CRM / Loyalty — Kokyaku (顧客 — "Customer")

| Field | Value |
|-------|-------|
| Persona | Kokyaku — Loyalty programs, customer segments, retention |
| gbrain source | `crm-retail/` |
| Skills | `loyalty-program`, `customer-segmentation` |
| Shared | `company-workflow`, `brain-compliance`, `slack-formatting` |
| Extra Crons | Points expiry review (daily 6AM) |

### Supply Chain — Ryutsu (流通 — "Distribution")

| Field | Value |
|-------|-------|
| Persona | Ryutsu — Warehousing, distribution, store replenishment |
| gbrain source | `supplychain/` |
| Skills | `warehouse-distribution`, `store-replenishment` |
| Shared | `company-workflow`, `brain-compliance`, `slack-formatting` |
| Extra Crons | Replenishment orders (daily 6AM) |

### Visual Merchandising — Hyoji (表示 — "Display")

| Field | Value |
|-------|-------|
| Persona | Hyoji — Store layouts, displays, planograms, signage |
| gbrain source | `vm/` |
| Skills | `planogram-compliance`, `promo-planning` |
| Shared | `company-workflow`, `brain-compliance`, `slack-formatting` |
| Extra Crons | Planogram compliance audit (Mon 7AM) |

---

## Detail: Shared Profiles

### 1. HR — Jinzai (人材 — "Talent")

| Field | Value |
|-------|-------|
| Persona | Jinzai — People Operations, culture builder |
| gbrain source | `hr/` |
| Skills | `mc-application`, `jibble-compliance`, `leave-balance`, `leave-management`, `people-ops` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Candidate pipeline (Mon 10AM), Recruitment GDrive sync (daily 6AM), Jibble attendance (weekdays 9:30AM), Jibble timesheet (Mon 10AM) |
| Task IDs | `HR-\\d+` |

### 2. Finance — Koku (石 — "Stone")

| Field | Value |
|-------|-------|
| Persona | Koku — Financial stability, budget discipline |
| gbrain source | `finance/` |
| Skills | (none beyond shared) |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Daily burn rate (8AM), Invoice aging (Mon 8AM), Monthly P&L (1st 8AM), Weekly budget (Mon 8AM) |
| Task IDs | `PO-\\d+`, `INV-\\d+` |

### 3. Procurement — Kura (蔵 — "Vault")

| Field | Value |
|-------|-------|
| Persona | Kura — Supply chain, vendor management, procurement optimization |
| gbrain source | `procurement/` |
| Skills | (none beyond shared) |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Contract expiry (Mon 9AM) |
| Task IDs | `PO-\\d+` |

### 4. CRM — Kizuna (絆 — "Bond")

| Field | Value |
|-------|-------|
| Persona | Kizuna — Client relationships, deal pipeline, account management |
| gbrain source | `crm/` |
| Skills | `crm-assistant`, `crm-deal-pipeline` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Deal activity sync (hourly 9-18), Sales pipeline (Mon 9AM), Weekly summary (Fri 5PM) |

### 5. Marketing — Haiku (俳句)

| Field | Value |
|-------|-------|
| Persona | Haiku — Brand, narrative, campaigns, presentations |
| gbrain source | `marketing/` |
| Skills | `your-company-deck`, `your-company-brand`, `campaign-manager`, `haiku`, `your-company-presentations`, `competitive-intel`, `roadmap` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |

### 6. Compliance — Kata (型 — "Form")

| Field | Value |
|-------|-------|
| Persona | Kata — Standards, audits, policy enforcement |
| gbrain source | `compliance/` |
| Skills | `compliance-policy-lifecycle` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |

### 7. Customer Support — Boei (防衛 — "Defense")

| Field | Value |
|-------|-------|
| Persona | Boei — Client shield, ticket resolution, escalation management |
| gbrain source | `support/` |
| Skills | `support-tickets` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Task IDs | `TS-20\\d{2}-\\d{3}` |

### 8. Coding Agent — Takumi (匠 — "Artisan")

| Field | Value |
|-------|-------|
| Persona | Takumi — Engineering craft, code quality, architecture |
| gbrain source | `engineering/` |
| Skills | `github-code-review`, `github-issues`, `simplify-code`, `code-review`, `debugging`, `skill-authoring`, `your-company-app-dev` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Scrum | ❌ (ad-hoc — no daily standup) |

### 9. Default Profile (Shared Infrastructure)

| Field | Value |
|-------|-------|
| Role | Shared resource orchestration |
| Crons | Email collector (30min), Email enrichment (9/13/17), Calendar sync (6AM), Calendar enrichment (8AM), Drive sync (12/16/20), Drive enrichment (13/17), Token utilization (Mon 8AM) |
| Auth | Google DWD service account |

### 10. Executive Assistant — Benkei (弁慶)

| Field | Value |
|-------|-------|
| Persona | Benkei (弁慶) — "The fiercely loyal retainer." Executive scheduling, travel, correspondence, identity-gated (serves CEO only) |
| gbrain source | `executive/` |
| Skills | `google-workspace` |
| Shared | `department-scrum`, `slack-formatting`, `brain-compliance`, `profile-enrichment` |
| Identity Config | `identities.yaml` — defines master, family, and privacy tiers |
| Scrum | ✅ 3-tier |

---

## Choosing an Industry

During `./install.sh --deploy all`, you'll be prompted to select your industry:

1. **General** (services, consulting, software) — deploys Projects + Product on top of shared profiles
2. **Manufacturing** (factory, production, OEM) — deploys Production, Quality, Maintenance, Warehouse, HSE on top of shared profiles

To skip the prompt, pass `--industry general` or `--industry manufacturing`:
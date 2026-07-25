# Profile Catalog

Shogun OS profiles are organized by **industry vertical**. All companies get the **shared profiles** (HR, Finance, CRM, etc.), then pick an industry for department-specific agents.

Each department Hermes profile exposes a **local gateway** used by the web portal chat UI, Slack, and MCP tooling. Default gateway ports come from `templates/web-portal/config.yaml` / `templates/web-portal/web.json` (9101–9110 for shared depts). `scripts/generate-profile.py` can also write `~/.hermes/profiles/<name>/.gateway-port` (auto: `8001 + type index` unless `--gateway-port` is set) — keep those values aligned with the portal config.

---

## Shared Profiles (Every Industry)

These 8 department profiles + default infrastructure + executive assistant are deployed for **every** company regardless of industry.

| # | Profile | Persona | Kanji | Role | Profile slug | Gateway port |
|---|---------|---------|-------|------|--------------|--------------|
| 1 | HR | Jinzai | 人材 — "Talent" | People operations, leave, recruitment | `hr-manager` | **9101** |
| 2 | Finance | Koku | 石 — "Stone" | Budget, cost, financial reporting | `finance-manager` | **9102** |
| 3 | Procurement | Kura | 蔵 — "Vault" | Supply chain, vendor management | `procurement-manager` | **9103** |
| 4 | CRM | Kizuna | 絆 — "Bond" | Client relationships, deal pipeline | `crm-manager` | **9104** |
| 5 | Marketing | Haiku | 俳句 | Brand, campaigns, content | `marketing-manager` | **9105** |
| 6 | Compliance | Kata | 型 — "Form" | Standards, audits, policy | `compliance-manager` | **9106** |
| 7 | Customer Support | Boei | 防衛 — "Defense" | Tickets, SLAs, escalation | `customer-support` | **9107** |
| 8 | Coding | Takumi | 匠 — "Artisan" | Engineering, code quality | `coding-agent` | **9110** |
| — | Default | — | — | Shared infrastructure crons | `default` | (no dept card; host infra) |
| — | Executive | Benkei | 弁慶 | CEO scheduling, travel, correspondence | `executive-assistant` | (optional / deploy-specific) |

General-industry add-ons (same port map as portal template):

| Profile | Persona | Profile slug | Gateway port |
|---------|---------|--------------|--------------|
| Projects | Gorobei | `project-manager` | **9108** |
| Product | Shi | `product-manager` | **9109** |

> **Web portal server** default bind: `0.0.0.0:8787` (`SHOGUN_WEB_PORT`, `~/.shogun-os/web.json`). Public URL: `https://<subdomain>.shogun-os.ai` (or `*.shogun.os` in local templates).

---

## Web Portal — How Profiles Appear in the UI (v3.10.0)

The multi-tenant portal lives in `shogun-web/` (`server/` FastAPI, `ui/` React, `registry/` central router). Install with `./scripts/install-web.sh`; verify with `./scripts/verify-web.sh`. Config templates: `templates/web-portal/config.yaml`, `templates/web-portal/web.json`.

### Tenant surface

| Surface | What users see |
|---------|----------------|
| Login | Google / Microsoft OAuth and/or email+password (forced password change on first login when configured) |
| Onboarding wizard | 4 steps: departments → company info → provider config → launch |
| Home / org | Company name, enabled departments, onboarding status |
| Department card | Persona-aligned department (HR, Finance, …) with status (`pending` / active / inactive) |
| Department hub | **Chat**, **Brain**, **Docs** tabs per department |
| Chat | Proxies to that profile’s Hermes **gateway port** |
| Brain | Reads/writes the department gbrain source (federated read of `shared/` where enabled) |
| Docs / providers | Domain provider abstraction config (e.g. accounting Bukku/QBO/Xero, HR Jibble) |

### Department ↔ UI mapping (defaults)

| UI department name | Hermes profile | Gateway port | Provider skill / recipe |
|--------------------|----------------|--------------|-------------------------|
| HR | `hr-manager` | 9101 | `time-tracking` → `recipes/hr/time-tracking/` |
| Finance | `finance-manager` | 9102 | `accounting-provider` → `recipes/accounting/` |
| Procurement | `procurement-manager` | 9103 | `procurement-provider` → `recipes/procurement/` |
| CRM | `crm-manager` | 9104 | `crm-provider` → `recipes/crm/` |
| Marketing | `marketing-manager` | 9105 | `marketing-provider` → `recipes/marketing/` |
| Compliance | `compliance-manager` | 9106 | `compliance-provider` → `recipes/compliance/` |
| Customer Support | `customer-support` | 9107 | `support-provider` → `recipes/support/` |
| Project | `project-manager` | 9108 | `projects-provider` → `recipes/projects/` |
| Product | `product-manager` | 9109 | `product-provider` → `recipes/product/` |
| Coding | `coding-agent` | 9110 | `engineering-provider` → `recipes/engineering/` |

Only **enabled** departments from onboarding are active in the UI. Industry-specific profiles (manufacturing / retail) appear when deployed; assign unique gateway ports in `~/.shogun-os/config.yaml` and re-register the tenant if needed.

### Install / ops quick ref

```bash
./scripts/install-web.sh          # build UI, write ~/.shogun-os/web.json + config, optional registry register
./scripts/verify-web.sh           # build, config, local HTTP, department ports
# Local: http://127.0.0.1:8787
# Public: https://<subdomain>.shogun-os.ai  (via registry + Cloudflare Tunnel)
```

Central registry (`shogun-web/registry/`) maps `*.shogun-os.ai` → tenant backends. Heartbeats and department/gateway metadata are stored per tenant.

---

## Provider Abstractions (v3.9.0)

Domain backends are **not** hard-coded into profiles. Each domain ships:

- `CONTRACT.md` — stable MCP tool names (`tt_*`, `acct_*`, `proc_*`, …)
- `GENERIC_SKILL.md` — agent-facing skill text
- `providers/` — per-vendor setup
- `plugins/` + bridge — `importlib` plugin load, env-var config, optional shared OAuth cache under `~/.hermes/mcp-tokens/`

| Domain | Recipe path | Tool prefix | Example providers |
|--------|-------------|-------------|-------------------|
| HR / time-tracking | `recipes/hr/time-tracking/` | `tt_*` | Jibble, Kami |
| Accounting | `recipes/accounting/` | `acct_*` | Bukku, QuickBooks, Xero |
| Procurement | `recipes/procurement/` | `proc_*` | (plugin slot) |
| CRM | `recipes/crm/` | `crm_*` | HubSpot, … |
| Marketing | `recipes/marketing/` | `mkt_*` | (plugin slot) |
| Compliance | `recipes/compliance/` | `comp_*` | (plugin slot) |
| Support | `recipes/support/` | `spt_*` | (plugin slot) |
| Engineering | `recipes/engineering/` | `eng_*` | (plugin slot) |
| Projects | `recipes/projects/` | `proj_*` | (plugin slot) |
| Product | `recipes/product/` | `pd_*` | (plugin slot) |

Guide: [`docs/recipes/creating-provider-abstractions.md`](docs/recipes/creating-provider-abstractions.md) · Architecture: [`docs/architecture/PROVIDER_ABSTRACTION.md`](docs/architecture/PROVIDER_ABSTRACTION.md)

⚠️ Standalone `recipes/jibble-time-tracking.md` is **deprecated** — use `recipes/hr/time-tracking/`.

---

## General Industry (Services, Consulting, Software)

These profiles handle project delivery and product management — the core of services companies.

### Projects — Gorobei (五郎兵衛 — "Strategist")

| Field | Value |
|-------|-------|
| Persona | Gorobei — Project execution, delivery management |
| Profile slug | `project-manager` |
| Gateway port | **9108** |
| Web UI | Department **Project** — Chat / Brain / Docs |
| gbrain source | `projects/` |
| Skills | `risk-scorer`, `gantt-renderer`, `meeting-extractor`, `pm-interview`, `procurement-planner`, `projects-provider` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/projects/` (`proj_*`) |
| Scrum | ✅ 3-tier — `scrum.yaml` included as example |
| Extra Crons | (none — scrum-only) |
| Task IDs | `TS-20\\d{2}-\\d{3}` |

### Product — Shi (志 — "Will")

| Field | Value |
|-------|-------|
| Persona | Shi — Product vision, feature prioritization, stakeholder alignment |
| Profile slug | `product-manager` |
| Gateway port | **9109** |
| Web UI | Department **Product** — Chat / Brain / Docs |
| gbrain source | `products/` |
| Skills | `competitive-intel`, `roadmap`, `brainstorming`, `product-provider` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/product/` (`pd_*`) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Sprint cycle (bi-weekly Mon) |
| Task IDs | `SAM-\\d{2}-\\d{2}-\\d{3,4}`, `INT-\\d+`, `EP-\\d+` |

---

## Manufacturing Industry (Factory, Production, OEM)

These profiles handle factory floor operations, quality control, maintenance, warehouse, and HSE — the core of manufacturing companies.

Assign **unique gateway ports** above 9110 (or free ports) in the web portal department list when enabling these profiles in the UI.

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
| Profile slug | `hr-manager` |
| Gateway port | **9101** |
| Web UI | Department **HR** |
| gbrain source | `hr/` |
| Skills | `mc-application`, `jibble-compliance`, `leave-balance`, `leave-management`, `people-ops`, `time-tracking` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/hr/time-tracking/` (`tt_*`; Jibble via `providers/jibble.md`) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Candidate pipeline (Mon 10AM), Recruitment GDrive sync (daily 6AM), Time tracking attendance (weekdays 9:30AM), Time tracking timesheet (Mon 10AM) |
| Task IDs | `HR-\\d+` |

### 2. Finance — Koku (石 — "Stone")

| Field | Value |
|-------|-------|
| Persona | Koku — Financial stability, budget discipline |
| Profile slug | `finance-manager` |
| Gateway port | **9102** |
| Web UI | Department **Finance** |
| gbrain source | `finance/` |
| Skills | `accounting-provider` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/accounting/` (`acct_*`; Bukku / QuickBooks / Xero bridge) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Daily burn rate (8AM), Invoice aging (Mon 8AM), Monthly P&L (1st 8AM), Weekly budget (Mon 8AM) |
| Task IDs | `PO-\\d+`, `INV-\\d+` |

### 3. Procurement — Kura (蔵 — "Vault")

| Field | Value |
|-------|-------|
| Persona | Kura — Supply chain, vendor management, procurement optimization |
| Profile slug | `procurement-manager` |
| Gateway port | **9103** |
| Web UI | Department **Procurement** |
| gbrain source | `procurement/` |
| Skills | `procurement-provider` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/procurement/` (`proc_*`) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Contract expiry (Mon 9AM) |
| Task IDs | `PO-\\d+` |

### 4. CRM — Kizuna (絆 — "Bond")

| Field | Value |
|-------|-------|
| Persona | Kizuna — Client relationships, deal pipeline, account management |
| Profile slug | `crm-manager` |
| Gateway port | **9104** |
| Web UI | Department **CRM** |
| gbrain source | `crm/` |
| Skills | `crm-assistant`, `crm-deal-pipeline`, `crm-provider`, `customer-communication-onboarding`, `respondio-bridge`, `chatwoot-bridge` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/crm/` (`crm_*`) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Extra Crons | Deal activity sync (hourly 9-18), Sales pipeline (Mon 9AM), Weekly summary (Fri 5PM) |

### 5. Marketing — Haiku (俳句)

| Field | Value |
|-------|-------|
| Persona | Haiku — Brand, narrative, campaigns, presentations |
| Profile slug | `marketing-manager` |
| Gateway port | **9105** |
| Web UI | Department **Marketing** |
| gbrain source | `marketing/` |
| Skills | `your-company-deck`, `your-company-brand`, `campaign-manager`, `haiku`, `your-company-presentations`, `competitive-intel`, `roadmap`, `marketing-provider` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/marketing/` (`mkt_*`) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |

### 6. Compliance — Kata (型 — "Form")

| Field | Value |
|-------|-------|
| Persona | Kata — Standards, audits, policy enforcement |
| Profile slug | `compliance-manager` |
| Gateway port | **9106** |
| Web UI | Department **Compliance** |
| gbrain source | `compliance/` |
| Skills | `compliance-policy-lifecycle`, `compliance-provider` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/compliance/` (`comp_*`) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |

### 7. Customer Support — Boei (防衛 — "Defense")

| Field | Value |
|-------|-------|
| Persona | Boei — Client shield, ticket resolution, escalation management |
| Profile slug | `customer-support` |
| Gateway port | **9107** |
| Web UI | Department **Customer Support** |
| gbrain source | `support/` |
| Skills | `support-tickets`, `support-provider` |
| Shared | `department-scrum`, `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/support/` (`spt_*`) |
| Scrum | ✅ 3-tier — `scrum.yaml` needed |
| Task IDs | `TS-20\\d{2}-\\d{3}` |

### 8. Coding Agent — Takumi (匠 — "Artisan")

| Field | Value |
|-------|-------|
| Persona | Takumi — Engineering craft, code quality, architecture |
| Profile slug | `coding-agent` |
| Gateway port | **9110** |
| Web UI | Department **Coding** |
| gbrain source | `engineering/` |
| Skills | `github-code-review`, `github-issues`, `simplify-code`, `code-review`, `debugging`, `skill-authoring`, `your-company-app-dev`, `engineering-provider` |
| Shared | `slack-formatting`, `staff-lookup`, `task-management`, `brain-compliance`, `profile-enrichment` |
| Provider recipe | `recipes/engineering/` (`eng_*`) |
| Scrum | ❌ (ad-hoc — no daily standup) |

### 9. Default Profile (Shared Infrastructure)

| Field | Value |
|-------|-------|
| Role | Shared resource orchestration |
| Profile slug | `default` |
| Gateway port | N/A (infra; not a portal department card) |
| Crons | Email collector (30min), Email enrichment (9/13/17), Calendar sync (6AM), Calendar enrichment (8AM), Drive sync (12/16/20), Drive enrichment (13/17), Token utilization (Mon 8AM) |
| Auth | Google DWD service account |
| Web | Hosts shared pipelines that feed department brains; portal users do not chat as “default” |

### 10. Executive Assistant — Benkei (弁慶)

| Field | Value |
|-------|-------|
| Persona | Benkei (弁慶) — "The fiercely loyal retainer." Executive scheduling, travel, correspondence, identity-gated (serves CEO only) |
| Profile slug | `executive-assistant` |
| Gateway port | Deploy-specific (not in default 9101–9110 portal list; add manually if exposed in UI) |
| gbrain source | `executive/` |
| Skills | `google-workspace` |
| Shared | `department-scrum`, `slack-formatting`, `brain-compliance`, `profile-enrichment` |
| Identity Config | `identities.yaml` — defines master, family, and privacy tiers |
| Scrum | ✅ 3-tier |

---

## Choosing an Industry

During `./scripts/install.sh --deploy`, you'll be prompted to select your industry (`--deploy` is boolean; do not pass `--deploy all`):

1. **General** (services, consulting, software) — deploys Projects + Product on top of shared profiles (~10 profiles)
2. **Manufacturing** (factory, production, OEM) — deploys Production, Quality, Maintenance, Warehouse, HSE on top of shared profiles (~13 profiles)
3. **Retail** (stores, e-commerce, omnichannel) — deploys Stores, Merchandising, E-commerce, CRM-Loyalty, Supply Chain, VM (~14 profiles)

To skip the prompt:

```bash
./scripts/install.sh --deploy --industry general
./scripts/install.sh --deploy --industry manufacturing
./scripts/install.sh --deploy --industry retail
```

Then set up the portal (optional but recommended):

```bash
./scripts/install-web.sh
./scripts/verify-web.sh
```

After profiles exist, keep **portal department ports** (`9101`–`9110` defaults) in sync with each profile’s running Hermes gateway and any `.gateway-port` file under `~/.hermes/profiles/<slug>/`.

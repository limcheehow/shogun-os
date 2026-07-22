# Shogun OS — Retail Industry

> **6 dedicated department agents for retail, e-commerce, and omnichannel operations. Deployed alongside the 8 shared profiles for a total of 14 autonomous AI agents.**

---

## Overview

The retail vertical adds 6 Samurai-themed department agents on top of the shared profiles (HR, Finance, Procurement, CRM, Marketing, Compliance, Support, Engineering). Together they cover the full retail value chain: stores, merchandising, e-commerce, CRM/loyalty, supply chain, and visual merchandising.

**Deploy:**
```bash
./scripts/install.sh --deploy all --industry retail
```

---

## Retail Profiles

### Stores — Tenpo (店舗 — "Shop")

| Field | Value |
|-------|-------|
| **Role** | Store operations, daily sales, staff scheduling, customer experience |
| **gbrain source** | `stores/` |
| **Skills** | `store-sales-dashboard`, `store-staff-scheduling`, `store-replenishment` |
| **Crons** | Daily sales report (6AM), staff scheduling (weekly Mon) |

**Persona:** Tenpo runs the retail floor. Every register, every customer, every sales associate — the pulse of the store. Not the one who buys — the one who sells, at the front line, every day.

### Merchandising — Shōhin (商品 — "Goods")

| Field | Value |
|-------|-------|
| **Role** | Buying, assortment planning, vendor negotiation, pricing |
| **gbrain source** | `merchandising/` |
| **Skills** | `assortment-planning`, `vendor-negotiation`, `promo-planning` |
| **Crons** | Slow-movers report (Mon 6AM), vendor contract expiry (Mon 9AM) |

**Persona:** Shōhin decides what sells and at what margin. Every SKU, every vendor, every promotion — the assortment is owned. The bridge between the market and the shelf.

### E-commerce — Denshi (電子 — "Digital")

| Field | Value |
|-------|-------|
| **Role** | Online store management, Shopee/Lazada/TikTok, listings, orders |
| **gbrain source** | `ecommerce/` |
| **Skills** | `ecommerce-listing`, `ecommerce-order-management`, `marketplace-analytics` |
| **Crons** | New orders consolidation (hourly 9-18), listing compliance check (daily 7AM) |

**Persona:** Denshi runs the online store. Shopee, Lazada, TikTok Shop — every platform, every listing, every order — managed from one place.

### CRM / Loyalty — Kokyaku (顧客 — "Customer")

| Field | Value |
|-------|-------|
| **Role** | Loyalty programs, customer segmentation, retention campaigns |
| **gbrain source** | `crm-retail/` |
| **Skills** | `loyalty-program`, `customer-segmentation` |
| **Crons** | Points expiry review (daily 6AM), churn signals report (weekly Mon) |

**Persona:** Kokyaku knows every customer, their preferences, their purchase history, and their lifetime value. Loyalty built through personalization, not discounts.

### Supply Chain — Ryutsū (流通 — "Distribution")

| Field | Value |
|-------|-------|
| **Role** | Warehousing, distribution, store replenishment, logistics |
| **gbrain source** | `supplychain/` |
| **Skills** | `warehouse-distribution`, `store-replenishment` |
| **Crons** | Replenishment orders (daily 6AM), warehouse pick-pack queue (hourly) |

**Persona:** Ryutsū moves goods from supplier to warehouse to store. Every PO, every shipment, every replenishment — the flow keeps moving.

### Visual Merchandising — Hyōji (表示 — "Display")

| Field | Value |
|-------|-------|
| **Role** | Store layout, displays, planograms, signage, brand standards |
| **gbrain source** | `vm/` |
| **Skills** | `planogram-compliance`, `promo-planning` |
| **Crons** | Planogram compliance audit (weekly Mon), promo display allocation (weekly) |

**Persona:** Hyōji shapes how the store looks and feels. Every display, every sign, every planogram — the visual experience that drives sales.

---

## Retail Skill Library

| Skill | Profile | What It Does |
|-------|---------|-------------|
| `store-sales-dashboard` | Tenpo | Daily sales by store, hourly trends, staff performance, customer count, budget variance |
| `store-staff-scheduling` | Tenpo | Shift planning, attendance, break compliance, labor cost vs sales ratio |
| `assortment-planning` | Shōhin | Category performance, SKU rationalization, new product intake calendar |
| `vendor-negotiation` | Shōhin | Vendor scorecards, margin analysis, contract expiry, rebate tracking |
| `ecommerce-listing` | Denshi | Product listing sync to Shopee/Lazada, image/SKU compliance |
| `ecommerce-order-management` | Denshi | Cross-platform order consolidation, fulfillment, returns |
| `marketplace-analytics` | Denshi | Sales by platform, ad spend ROI, competitor pricing, review sentiment |
| `loyalty-program` | Kokyaku | Points accrual, tier management, birthday/promotion triggers |
| `customer-segmentation` | Kokyaku | RFM analysis, churn prediction, lookalike targeting |
| `store-replenishment` | Ryutsū | Auto-reorder by min/max, allocation per store cluster, lead time tracking |
| `warehouse-distribution` | Ryutsū | Inbound receiving, putaway, pick-pack-ship, cross-docking, wave planning |
| `planogram-compliance` | Hyōji | Store layout audits, shelf compliance scoring, photo validation |
| `promo-planning` | Hyōji | Promotional calendar, display allocation, signage generation |

---

## Integrations

| System | Type | Adapter | Capabilities |
|--------|------|---------|-------------|
| **AutoCount** | Accounting (MY) | REST (AOTG API) | Stock balances, sales invoices, debtor aging, purchase orders, e-invoice |
| **Shopee** | E-commerce (SEA) | Open Platform API v2 | Products, orders, returns, analytics, webhooks |
| **Lazada** | E-commerce (SEA) | Seller Center REST API | Products, orders, shipments, finance, seller performance |
| **TikTok Shop** | E-commerce | Seller API | Products, orders, fulfillment, affiliates |

---

## Daily Workflow

```
6:00 AM  Tenpo    → Previous day sales, store readiness, staff attendance
6:00 AM  Shōhin   → Slow-movers report, vendor overdue deliveries, promo expiry
Hourly   Denshi   → New Shopee/Lazada orders, fulfillment queue, return requests
6:00 AM  Kokyaku  → Points expiry, birthday triggers, churn signals
6:00 AM  Ryutsū   → Store replenishment orders, warehouse pick-pack queue
Weekly   Hyōji    → Planogram compliance audit, promo display allocation
```

---

## Related Pages

- [Shared Profiles (README)](README.md)
- [PROFILE_CATALOG.md](PROFILE_CATALOG.md)
- [CRON_INVENTORY.md](CRON_INVENTORY.md)
- [SETUP.md](SETUP.md)
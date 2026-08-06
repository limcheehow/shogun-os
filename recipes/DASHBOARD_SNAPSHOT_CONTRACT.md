# Dashboard Snapshot Contract

Locks the slug + JSON field names the department **snapshot-writer** skills must
emit and the dashboard backend (`server/dashboard.py`) reads. This closes the
gap that previously left both dashboards on mock data (Concern 5 in
`TO-DO-PD.md`).

## Invariants

1. ** Snapshots**: gbrain pages whose slug is `<dept>/snapshots/<name>.json`
   with a JSON object as the page body (the backend parses both frontmatter and
   JSON body — see `dashboard.py:_run_*_aggregation`).
2. **Casing**: snapshot fields are **snake_case**. The dashboard API response
   (what the frontend consumes) is **camelCase**. The backend owns the
   normalization. Skills write snake_case only.
3. **Fallback contract** (must hold for both dashboards):
   - Snapshot present + non-empty → render live data.
   - Snapshot absent OR empty → render mock from
     `examples/<dept>-mock.json` (`dashboard_mock` key) / `examples/finance-budget.json`.
     No 500, no empty screens.
   - Agent gateway down → snapshot skill cannot run → stays on mock
     (acceptable degradation).
4. **Idempotency**: snapshot-writer skills overwrite each snapshot page on
   every run. Empty brain → write snapshots with zeros / empty arrays, exit 0
   (never crash).

## Procurement slugs

Backend reads at `dashboard.py` `_run_procurement_aggregation`
(`snapshots/<name>` or `procurement/snapshots/<name>`).

### `procurement/snapshots/inventory.json`
```json
{
  "total_inventory_valuation": 1850000.0,
  "total_active_skus": 1248,
  "low_stock_alerts": 7,
  "dead_slow_stock_capital": 285000.0,
  "procurement_spend_mtd": 348000.0,
  "procurement_spend_budget_mtd": 380000.0,
  "valuation_by_category": [{ "category": "IT Hardware", "value": 612000.0 }],
  "sku_catalog": [{
    "sku": "IT-LP-15",
    "item_name": "Dell Latitude 5540 i7",
    "category": "IT Hardware",
    "unit_cost": 4200.00,
    "current_qty": 4,
    "safety_reorder_point": 12,
    "location_bin": "LOC-MAIN-A1",
    "status": "Low Stock"
  }],
  "dead_slow_stock": [{
    "sku": "SP-HD-44", "item_name": "HDD 4TB WD Red", "category": "Spare Parts",
    "current_qty": 52, "days_since_last_movement": 214,
    "months_of_cover": 13.2, "total_tied_value": 35360.0,
    "action_recommendation": "Bundle Promo with Top SKU"
  }],
  "warehouse_bin_capacity": [{
    "location": "LOC-MAIN-A1", "used": 4, "capacity": 1200, "utilisation_pct": 0.3
  }],
  "spend_vs_budget_trend": [{ "month": "2026-01", "spend": 320000.0, "budget": 380000.0 }],
  "risk_alerts": [{ "type": "safety_breach", "level": "critical", "message": "..." }]
}
```
- `sku_catalog[]` has **no `selling_price`** (Choice D, Concern 7 of `TO-DO-PD.md`).
- ABC Pareto is **NOT** in any snapshot — it is computed client-side from
  `sku_catalog` (Phase 1 of `TO-DO-PD.md`).

### `procurement/snapshots/purchase-orders.json`
```json
{
  "open_po_count": 14,
  "open_po_value": 412000.0,
  "po_pipeline": [{ "stage": "Draft", "count": 3, "value": 58000.0 }],
  "active_purchase_orders": [{
    "po_number": "PO-2026-0199", "vendor": "Pacific Hardware Co",
    "order_date": "2026-07-26", "expected_delivery": "2026-08-22",
    "total_amount": 12480.0,
    "fulfillment_status": "Draft", "approval_status": "Draft"
  }],
  "executive_approval_queue": [{
    "po_number": "PO-2026-0213", "vendor": "Aurora Furnishings Sdn Bhd",
    "order_date": "2026-08-04", "total_amount": 21400.0,
    "requester_dept": "Operations / Facilities", "threshold_myr": 10000,
    "approval_status": "Pending Executive Approval"
  }]
}
```
- `executive_approval_queue[]` only contains rows with `total_amount > 10000`.

### `procurement/snapshots/vendors.json`
```json
{
  "vendor_scorecard": [{
    "vendor": "NexTech Distribution Sdn Bhd", "preferred_category": "IT Hardware",
    "ytd_spend": 486000.0, "on_time_delivery_rate": 94.0,
    "quality_acceptance_rate": 97.0, "sla_status": "Top Tier"
  }],
  "vendor_spend_concentration": [{ "vendor": "NexTech Distribution Sdn Bhd", "spend": 486000.0, "spend_pct": 27.4 }]
}
```

### `procurement/snapshots/stock-movements.json`
```json
{
  "stock_movements": [{
    "timestamp": "2026-08-04T09:21:00Z", "sku": "IT-LP-15",
    "item_name": "Dell Latitude 5540 i7", "movement_type": "+ Receive",
    "quantity": 5, "reference_id": "PO-2026-0210",
    "location_id": "LOC-MAIN-A1", "actor": "koku"
  }],
  "movement_type_distribution": [{ "movement_type": "+ Receive", "count": 12, "quantity": 86 }],
  "shrinkage_flag_items": ["IT-LP-15"]
}
```
- Movements are listed via the `proc_list_stock_movements` tool
  (Phase 2.5.2 of `TO-DO-PD.md`).

### `procurement/snapshots/accounting-bridge.json`
```json
{
  "bridge_status": { "enabled": true, "provider": "Bukku", "connected": true, "last_sync": "2026-08-05T07:00:00Z" },
  "po_bill_conversion_queue": [{
    "po_number": "PO-2026-0188", "vendor": "Greenway Office Supply",
    "date_received": "2026-07-30", "total_amount": 9800.0,
    "sync_status": "Ready to Sync"
  }],
  "gl_valuation_reconciliation": [{
    "account_code": "1400", "physical_stock_value": 1850000.0,
    "gl_book_value": 1842000.0, "variance": 8000.0, "variance_pct": 0.43,
    "reconciliation_status": "Reconciled"
  }]
}
```
- `bridge_status` is **assembled by the snapshot-writer skill** (Choice A,
  Concern 6 of `TO-DO-PD.md`): `enabled` ← `ENABLE_ACCOUNTING_SYNC` env var,
  `provider` ← `ACCT_PROVIDER`, `last_sync` ← newest `procurement/reports/gl-sync-*.md`
  timestamp, `connected` ← probe `acct_get_balance_sheet`. There is **no**
  dedicated `proc_get_accounting_bridge_status` tool by design.

## Finance slugs

Backend reads at `dashboard.py` `_run_finance_aggregation`
(`snapshots/<name>` or `finance/snapshots/<name>`).

### `finance/snapshots/cash.json`
```json
{
  "total_liquid_cash": 1240000.0,
  "net_monthly_burn": 95000.0,
  "cash_runway_months": 13.0,
  "fixed_opex": 78000.0,
  "variable_opex": 22000.0,
  "bank_accounts": [{ "name": "Maybank Current", "balance": 820000.0, "currency": "MYR" }],
  "fx_positions": [{ "currency": "USD", "amount": 12500.0, "myr_value": 58125.0 }],
  "forecast_13w": {
    "conservative": [{ "week": "2026-W33", "closing": 1100000.0 }],
    "expected":     [{ "week": "2026-W33", "closing": 1180000.0 }],
    "optimistic":    [{ "week": "2026-W33", "closing": 1260000.0 }]
  },
  "cash_flow_trend": [{ "month": "2026-07", "inflow": 420000.0, "outflow": 348000.0 }]
}
```

### `finance/snapshots/pl.json`
```json
{
  "revenue_mtd": 410000.0,
  "revenue_ytd": 2980000.0,
  "gross_margin_pct": 42.0,
  "ebitda_margin_pct": 18.0,
  "unpaid_statutory": 32000.0,
  "revenue_opex_trend": [{ "month": "2026-07", "revenue": 410000.0, "opex": 245000.0 }]
}
```

### `finance/snapshots/concentration.json`
```json
{
  "clients": [{ "name": "Acme Corp", "revenue_pct": 28.4, "ytd_revenue": 846000.0 }]
}
```
- `revenue_pct > 20` triggers a concentration risk alert in the backend.

### `finance/snapshots/bva.json`
```json
{
  "departments": [{ "department": "Engineering", "variance_pct": 12.4 }],
  "unit_economics": {
    "gross_margin_pct": 42.0, "contribution_margin_pct": 23.0,
    "cac": 4200.0, "ltv": 28000.0, "ltv_cac_ratio": 6.7
  }
}
```
- `variance_pct > 10` triggers an OPEX overrun alert.

### `finance/snapshots/ar.json`
```json
{
  "total_ar": 612000.0,
  "bucket_0_30": 340000.0,
  "bucket_31_60": 180000.0,
  "bucket_61_90": 68000.0,
  "bucket_90_plus": 24000.0,
  "dso": 41.0,
  "dunning_queue": [{ "invoice": "INV-2026-0888", "client": "Acme Corp", "amount": 18000.0, "days_overdue": 96 }]
}
```

### `finance/snapshots/ap.json`
```json
{
  "total_ap": 248000.0,
  "ap_overdue": 32000.0,
  "dpo": 38.0,
  "bills": [{ "bill": "BILL-2026-0421", "vendor": "NexTech Distribution", "amount": 12400.0, "due_date": "2026-08-12" }]
}
```

### `finance/snapshots/compliance.json`
```json
{
  "close_checklist": [{ "item": "Bank reconciliations", "status": "done" }],
  "statutory_schedule": [{ "obligation": "SST Q3 return", "due": "2026-09-30", "status": "pending" }],
  "sst_readiness": { "draft_status": "drafted", "taxable_sales": 410000.0, "sst_liability": 24600.0 },
  "cp58_register": [{ "vendor": "NexTech Distribution", "ytd_paid": 486000.0 }],
  "wht_queue": [{ "payment": "PMT-2026-0901", "amount": 5000.0, "rate_pct": 10.0 }],
  "expense_claim_audit": [{ "claim": "EXP-2026-0123", "amount": 480.0, "flag": "missing_receipt" }]
}
```

## Skills that write snapshots

- `skills/procurement/dashboard-snapshot-writer/` — writes the 5 procurement
  snapshots above on a daily cron + `/refresh-procurement-dashboard` trigger.
- `skills/finance/dashboard-snapshot-writer/` — writes the 7 finance snapshots
  above on a daily cron + `/refresh-finance-dashboard` trigger.

Both skills are idempotent and empty-brain-safe (Karpathy: empty input → write
zeros / empty arrays, exit 0 — never crash).
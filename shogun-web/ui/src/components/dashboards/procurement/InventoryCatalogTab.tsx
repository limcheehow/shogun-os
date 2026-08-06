import { useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';
import type { AbcParetoClass, ProcurementDashboardStats, SkuItem } from '../../../lib/types';

interface Props {
  stats: ProcurementDashboardStats;
  color: string;
  onAction?: (actionType: string, entity: unknown) => void;
}

const fmtMyr = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function computeAbcPareto(catalog: SkuItem[]): AbcParetoClass[] {
  const items = catalog
    .map((s) => ({ sku: s.sku, value: (s.unit_cost || 0) * (s.current_qty || 0) }))
    .filter((it) => it.value > 0)
    .sort((a, b) => b.value - a.value);
  const total = items.reduce((sum, it) => sum + it.value, 0);
  if (total <= 0 || items.length === 0) {
    return [
      { class_label: 'A', sku_count: 0, sku_pct: 0, capital_value: 0, value_pct: 0 },
      { class_label: 'B', sku_count: 0, sku_pct: 0, capital_value: 0, value_pct: 0 },
      { class_label: 'C', sku_count: 0, sku_pct: 0, capital_value: 0, value_pct: 0 },
    ];
  }
  const classes: AbcParetoClass[] = [
    { class_label: 'A', sku_count: 0, sku_pct: 0, capital_value: 0, value_pct: 0 },
    { class_label: 'B', sku_count: 0, sku_pct: 0, capital_value: 0, value_pct: 0 },
    { class_label: 'C', sku_count: 0, sku_pct: 0, capital_value: 0, value_pct: 0 },
  ];
  let cumulative = 0;
  for (const it of items) {
    cumulative += it.value;
    const share = cumulative / total;
    let idx: number;
    if (share <= 0.80) idx = 0;
    else if (share <= 0.95) idx = 1;
    else idx = 2;
    classes[idx].sku_count += 1;
    classes[idx].capital_value += it.value;
  }
  const totalSkus = items.length;
  classes.forEach((c) => {
    c.sku_pct = totalSkus > 0 ? (c.sku_count / totalSkus) * 100 : 0;
    c.value_pct = total > 0 ? (c.capital_value / total) * 100 : 0;
  });
  return classes;
}

const ABC_STYLE: Record<string, string> = {
  A: 'bg-emerald-100 text-emerald-700',
  B: 'bg-blue-100 text-blue-700',
  C: 'bg-slate-100 text-slate-600',
};

const STATUS_STYLE: Record<string, string> = {
  'In Stock':     'bg-emerald-100 text-emerald-700',
  'Low Stock':    'bg-amber-100 text-amber-700',
  'Out of Stock': 'bg-rose-100 text-rose-700',
  'Overstocked':  'bg-blue-100 text-blue-700',
};

const ACTION_STYLE: Record<string, string> = {
  '25% Promo Discount':          'bg-amber-100 text-amber-700',
  'Vendor Clearance Return':     'bg-blue-100 text-blue-700',
  'Bundle Promo with Top SKU':   'bg-indigo-100 text-indigo-700',
  'Scrap / Write-off':           'bg-rose-100 text-rose-700',
};

export function InventoryCatalogTab({ stats, onAction }: Props) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [skuActionTarget, setSkuActionTarget] = useState<SkuItem | null>(null);

  const categories = useMemo(
    () => Array.from(new Set(stats.skuCatalog.map((s) => s.category))).sort(),
    [stats.skuCatalog],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return stats.skuCatalog.filter((s: SkuItem) => {
      if (q && !s.sku.toLowerCase().includes(q) && !s.item_name.toLowerCase().includes(q)) return false;
      if (category !== 'all' && s.category !== category) return false;
      if (statusFilter !== 'all' && s.status !== statusFilter) return false;
      return true;
    });
  }, [stats.skuCatalog, query, category, statusFilter]);

  const abcClasses = useMemo(() => computeAbcPareto(stats.skuCatalog), [stats.skuCatalog]);
  const abcTotalCapital = abcClasses.reduce((sum, c) => sum + c.capital_value, 0);

  return (
    <div className="space-y-4">
      {/* SKU Catalog & Search Table */}
      <div className="card p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h3 className="mr-auto text-sm font-semibold text-slate-700">SKU Catalog</h3>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search SKU or item name…"
              className="w-56 rounded-md border border-surface-border bg-white pl-8 pr-3 py-1.5 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand focus:outline-none"
            />
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-md border border-surface-border bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-brand focus:outline-none"
          >
            <option value="all">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-surface-border bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-brand focus:outline-none"
          >
            <option value="all">All Status</option>
            <option value="In Stock">In Stock</option>
            <option value="Low Stock">Low Stock</option>
            <option value="Out of Stock">Out of Stock</option>
            <option value="Overstocked">Overstocked</option>
          </select>
        </div>

        {filtered.length === 0 ? (
          <p className="text-sm text-slate-400">No SKUs match the current filters.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">SKU</th>
                  <th className="pb-2 text-left font-medium">Item Name</th>
                  <th className="pb-2 text-left font-medium">Category</th>
                  <th className="pb-2 text-right font-medium">Unit Cost</th>
                  <th className="pb-2 pl-6 text-right font-medium">Qty</th>
                  <th className="pb-2 text-right font-medium">Reorder Pt</th>
                  <th className="pb-2 text-left font-medium">Location/Bin</th>
                  <th className="pb-2 text-center font-medium">Status</th>
                  <th className="pb-2 text-center font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filtered.map((s) => (
                  <tr key={s.sku} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-mono text-xs font-medium text-slate-800">{s.sku}</td>
                    <td className="py-2 font-medium text-slate-800">{s.item_name}</td>
                    <td className="py-2 text-slate-600">{s.category}</td>
                    <td className="py-2 text-right text-slate-700">{fmtMyr(s.unit_cost)}</td>
                    <td className="py-2 pl-6 text-right font-semibold text-slate-900">{s.current_qty.toLocaleString()}</td>
                    <td className="py-2 text-right text-slate-600">{s.safety_reorder_point.toLocaleString()}</td>
                    <td className="py-2 font-mono text-xs text-slate-600">{s.location_bin}</td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[s.status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="py-2 text-center">
                      {(s.status === 'Low Stock' || s.status === 'Out of Stock') ? (
                        <button
                          type="button"
                          onClick={() => setSkuActionTarget(s)}
                          className="rounded-md bg-amber-500 px-3 py-1 text-xs font-bold text-white shadow-sm hover:bg-amber-600 transition-colors"
                        >
                          Send PR
                        </button>
                      ) : (
                        <span className="text-xs text-slate-300 italic">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Dunning-Style Inventory Action Modal */}
      {skuActionTarget && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default bg-black/30" onClick={() => setSkuActionTarget(null)} aria-label="Close" />
          <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16" onClick={() => setSkuActionTarget(null)}>
            <div className="card relative z-50 w-full max-w-md overflow-hidden bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Inventory Action</h2>
                  <p className="text-xs text-slate-500">{skuActionTarget.item_name} · {skuActionTarget.sku}</p>
                </div>
                <button type="button" onClick={() => setSkuActionTarget(null)} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 px-5 py-4 bg-slate-50/50">
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">Current Qty</div>
                  <div className="text-base font-bold text-rose-600">{skuActionTarget.current_qty.toLocaleString()} units</div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">Safety Reorder Point</div>
                  <div className="text-base font-bold text-slate-900">{skuActionTarget.safety_reorder_point.toLocaleString()} units</div>
                </div>
              </div>

              <div className="border-t border-surface-border px-5 py-4">
                <p className="mb-3 text-xs text-slate-500 font-medium">Select action to send to Chotatsu (Procurement Agent):</p>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('raise_pr_for_sku', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-amber-300 bg-amber-50/60 px-4 py-2.5 text-left text-sm font-semibold text-amber-900 hover:bg-amber-100 transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Send Purchase Requisition (PR)</span>
                    <span className="text-xs text-amber-600 font-bold">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('record_adjustment', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-surface-border bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:border-brand hover:text-brand transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Record Stock Adjustment</span>
                    <span className="text-xs text-slate-400">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('edit_sku', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-surface-border bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:border-brand hover:text-brand transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Edit SKU Details</span>
                    <span className="text-xs text-slate-400">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('draft_po', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-surface-border bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:border-brand hover:text-brand transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Draft Urgent PO</span>
                    <span className="text-xs text-slate-400">→</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* ABC Inventory Pareto Analysis */}
      <div className="card p-4">
        <div className="mb-1 flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-700">ABC Inventory Pareto Analysis</h3>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">client-side · skuCatalog</span>
        </div>
        <p className="mb-3 text-xs text-slate-400">
          Class A (≈80% of capital value), Class B (next ≈15%), Class C (remaining ≈5%). Capital value = unit cost × current qty; classes set by cumulative value breakpoints.
        </p>
        {abcTotalCapital <= 0 ? (
          <p className="text-sm text-slate-400">No SKUs with positive value to classify.</p>
        ) : (
          <div className="space-y-3">
            {abcClasses.map((c) => (
              <div key={c.class_label} className="rounded-lg border border-surface-border p-3">
                <div className="mb-2 flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${ABC_STYLE[c.class_label]}`}>Class {c.class_label}</span>
                  <span className="text-xs text-slate-500">
                    {c.sku_count.toLocaleString()} SKU{c.sku_count === 1 ? '' : 's'} · {c.sku_pct.toFixed(1)}% of items
                  </span>
                  <span className="ml-auto text-sm font-semibold text-slate-800">{fmtMyr(c.capital_value)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-2 rounded-full ${c.class_label === 'A' ? 'bg-emerald-500' : c.class_label === 'B' ? 'bg-blue-500' : 'bg-slate-400'}`}
                      style={{ width: `${Math.min(c.value_pct, 100)}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-xs font-medium text-slate-600">{c.value_pct.toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dead & Slow-Moving Stock Analysis Hub */}
      <div className="card p-4">
        <div className="mb-1 flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-700">Dead & Slow-Moving Stock Analysis</h3>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">P0 · dead-slow-stock-detector</span>
        </div>
        <p className="mb-3 text-xs text-slate-400">
          SKUs with &gt;8 months inventory cover (90-day velocity) or zero movement in &gt;180 days. Ranked by total capital tied up.
        </p>
        {stats.deadSlowStock.length === 0 ? (
          <p className="text-sm text-slate-400">No dead or slow-moving stock detected. Chotatsu (Procurement Agent) generates this from stock movement history.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">SKU & Item</th>
                  <th className="pb-2 text-left font-medium">Category</th>
                  <th className="pb-2 text-right font-medium">Qty</th>
                  <th className="pb-2 text-right font-medium">Days No Movement</th>
                  <th className="pb-2 text-right font-medium">Months Cover</th>
                  <th className="pb-2 text-right font-medium">Tied-Up Value</th>
                  <th className="pb-2 text-center font-medium">Flush Recommendation</th>
                  <th className="pb-2 text-center font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.deadSlowStock.map((d) => (
                  <tr key={d.sku} className="hover:bg-surface-muted/50">
                    <td className="py-2">
                      <div className="font-mono text-xs font-medium text-slate-800">{d.sku}</div>
                      <div className="text-xs text-slate-500">{d.item_name}</div>
                    </td>
                    <td className="py-2 text-slate-600">{d.category}</td>
                    <td className="py-2 text-right font-semibold text-slate-900">{d.current_qty.toLocaleString()}</td>
                    <td className="py-2 text-right text-slate-700">{d.days_since_last_movement}d</td>
                    <td className="py-2 text-right text-slate-700">{d.months_of_cover.toFixed(1)}</td>
                    <td className="py-2 text-right leading-tight">
                      <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">RM</div>
                      <div className="text-sm font-bold text-rose-600">
                        {d.total_tied_value >= 1_000_000
                          ? `${(d.total_tied_value / 1_000_000).toFixed(2)}M`
                          : d.total_tied_value >= 1_000
                            ? `${(d.total_tied_value / 1_000).toFixed(0)}K`
                            : d.total_tied_value.toLocaleString()}
                      </div>
                    </td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ACTION_STYLE[d.action_recommendation] ?? 'bg-slate-100 text-slate-600'}`}>
                        {d.action_recommendation}
                      </span>
                    </td>
                    <td className="py-2 text-center">
                      <button
                        type="button"
                        onClick={() => onAction?.('launch_dead_stock_action', d)}
                        className="rounded-md bg-brand px-3 py-1 text-xs font-semibold text-white hover:opacity-90 transition-opacity shadow-sm"
                      >
                        Launch
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

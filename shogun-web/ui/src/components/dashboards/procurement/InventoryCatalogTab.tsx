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
  A: 'ok',
  B: 'muted',
  C: 'muted',
};

const STATUS_STYLE: Record<string, string> = {
  'In Stock':     'ok',
  'Low Stock':    'warn',
  'Out of Stock': 'bad',
  'Overstocked':  'muted',
};

const ACTION_STYLE: Record<string, string> = {
  '25% Promo Discount':          'warn',
  'Vendor Clearance Return':    'muted',
  'Bundle Promo with Top SKU':   'muted',
  'Scrap / Write-off':           'bad',
};

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const BORDER = 'var(--samurai-border)';
const SURFACE_2 = 'var(--samurai-surface-2)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function InventoryCatalogTab({ stats, onAction }: Props) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [skuActionTarget, setSkuActionTarget] = useState<SkuItem | null>(null);
  const [deadStockTarget, setDeadStockTarget] = useState<any | null>(null);
  const [selectedComboStrategy, setSelectedComboStrategy] = useState<string>('bundle_top_sku');
  const [customIdeaInput, setCustomIdeaInput] = useState<string>('');

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
    <div className="sd-stack">
      {/* SKU Catalog & Search Table */}
      <div className="sd-chart-card">
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <h3 className="sd-chart-title" style={{ margin: 0, marginRight: 'auto' }}>SKU Catalog</h3>
          <div style={{ position: 'relative' }}>
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: MUTED }} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search SKU or item name…"
              style={{ width: '14rem', borderRadius: '0.5rem', border: `1px solid ${BORDER}`, background: 'var(--samurai-surface)', paddingLeft: '2rem', paddingRight: '0.75rem', paddingTop: '0.375rem', paddingBottom: '0.375rem', fontSize: '0.85rem', color: TEXT }}
            />
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{ borderRadius: '0.5rem', border: `1px solid ${BORDER}`, background: 'var(--samurai-surface)', color: TEXT, padding: '0.375rem 0.5rem', fontSize: '0.85rem' }}
          >
            <option value="all">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ borderRadius: '0.5rem', border: `1px solid ${BORDER}`, background: 'var(--samurai-surface)', color: TEXT, padding: '0.375rem 0.5rem', fontSize: '0.85rem' }}
          >
            <option value="all">All Status</option>
            <option value="In Stock">In Stock</option>
            <option value="Low Stock">Low Stock</option>
            <option value="Out of Stock">Out of Stock</option>
            <option value="Overstocked">Overstocked</option>
          </select>
        </div>

        {filtered.length === 0 ? (
          <p style={{ padding: '1rem 0', textAlign: 'center', fontSize: '0.85rem', color: MUTED }}>No SKUs match the current filters.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">SKU</Th>
                  <Th align="left">Item Name</Th>
                  <Th align="left">Category</Th>
                  <Th align="right">Unit Cost</Th>
                  <Th align="right">Qty</Th>
                  <Th align="right">Reorder Pt</Th>
                  <Th align="left">Location/Bin</Th>
                  <Th align="center">Status</Th>
                  <Th align="center">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => (
                  <tr key={s.sku} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-3 py-2" style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', fontWeight: 600, color: TEXT }}>{s.sku}</td>
                    <td className="px-3 py-2" style={{ fontWeight: 600, color: TEXT }}>{s.item_name}</td>
                    <td className="px-3 py-2" style={{ color: MUTED }}>{s.category}</td>
                    <td className="px-3 py-2 text-right" style={{ color: TEXT }}>{fmtMyr(s.unit_cost)}</td>
                    <td className="px-3 py-2 text-right" style={{ fontWeight: 600, color: TEXT }}>{s.current_qty.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right" style={{ color: MUTED }}>{s.safety_reorder_point.toLocaleString()}</td>
                    <td className="px-3 py-2" style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', color: MUTED }}>{s.location_bin}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={`sd-chip ${STATUS_STYLE[s.status] ?? 'muted'}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      {(s.status === 'Low Stock' || s.status === 'Out of Stock') ? (
                        <button
                          type="button"
                          onClick={() => setSkuActionTarget(s)}
                          className="sd-btn sd-btn-secondary"
                          style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem', color: 'var(--samurai-warning)' }}
                        >
                          Send PR
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.72rem', color: MUTED, fontStyle: 'italic' }}>—</span>
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
          <button type="button" style={{ position: 'fixed', inset: 0, zIndex: 40, background: 'rgba(0,0,0,0.4)', border: 'none', cursor: 'default' }} onClick={() => setSkuActionTarget(null)} aria-label="Close" />
          <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }} onClick={() => setSkuActionTarget(null)}>
            <div className="sd-card" style={{ position: 'relative', zIndex: 50, width: '100%', maxWidth: '26rem', height: 'fit-content', padding: '1.25rem' }} onClick={(e) => e.stopPropagation()}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.75rem', marginBottom: '0.75rem' }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: TEXT, margin: 0 }}>Inventory Action</h2>
                  <p style={{ fontSize: '0.72rem', color: MUTED, margin: 0 }}>{skuActionTarget.item_name} · {skuActionTarget.sku}</p>
                </div>
                <button type="button" className="sd-icon-btn" onClick={() => setSkuActionTarget(null)} aria-label="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <div style={{ borderRadius: '0.5rem', background: SURFACE_2, padding: '0.6rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: MUTED }}>Current Qty</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, color: 'var(--samurai-danger)' }}>{skuActionTarget.current_qty.toLocaleString()} units</div>
                </div>
                <div style={{ borderRadius: '0.5rem', background: SURFACE_2, padding: '0.6rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: MUTED }}>Safety Reorder Point</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, color: TEXT }}>{skuActionTarget.safety_reorder_point.toLocaleString()} units</div>
                </div>
              </div>

              <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: '0.75rem' }}>
                <p style={{ fontSize: '0.72rem', color: MUTED, marginBottom: '0.6rem' }}>Select action to send to Chotatsu (Procurement Agent):</p>
                <div className="sd-stack" style={{ gap: '0.4rem' }}>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('raise_pr_for_sku', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="sd-btn sd-btn-primary"
                    style={{ justifyContent: 'space-between' }}
                  >
                    <span>Send Purchase Requisition (PR)</span>
                    <span style={{ fontSize: '0.72rem' }}>→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('record_adjustment', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{ justifyContent: 'space-between' }}
                  >
                    <span>Record Stock Adjustment</span>
                    <span style={{ fontSize: '0.72rem' }}>→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('edit_sku', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{ justifyContent: 'space-between' }}
                  >
                    <span>Edit SKU Details</span>
                    <span style={{ fontSize: '0.72rem' }}>→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('draft_po', skuActionTarget);
                      setSkuActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{ justifyContent: 'space-between' }}
                  >
                    <span>Draft Urgent PO</span>
                    <span style={{ fontSize: '0.72rem' }}>→</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* ABC Inventory Pareto Analysis */}
      <div className="sd-chart-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <h3 className="sd-chart-title" style={{ margin: 0 }}>ABC Inventory Pareto Analysis</h3>
          <span className="sd-chip muted">client-side · skuCatalog</span>
        </div>
        <p className="sd-chart-sub">
          Class A (≈80% of capital value), Class B (next ≈15%), Class C (remaining ≈5%). Capital value = unit cost × current qty; classes set by cumulative value breakpoints.
        </p>
        {abcTotalCapital <= 0 ? (
          <p style={{ color: MUTED, fontSize: '0.85rem' }}>No SKUs with positive value to classify.</p>
        ) : (
          <div className="sd-stack" style={{ gap: '0.75rem' }}>
            {abcClasses.map((c) => (
              <div key={c.class_label} style={{ borderRadius: '0.5rem', border: `1px solid ${BORDER}`, padding: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <span className={`sd-chip ${ABC_STYLE[c.class_label] ?? 'muted'}`}>Class {c.class_label}</span>
                  <span style={{ fontSize: '0.72rem', color: MUTED }}>
                    {c.sku_count.toLocaleString()} SKU{c.sku_count === 1 ? '' : 's'} · {c.sku_pct.toFixed(1)}% of items
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: '0.85rem', fontWeight: 600, color: TEXT }}>{fmtMyr(c.capital_value)}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div style={{ height: '0.5rem', flex: 1, borderRadius: 999, overflow: 'hidden', background: SURFACE_2 }}>
                    <div
                      style={{ height: '100%', borderRadius: 999, background: c.class_label === 'A' ? 'var(--samurai-ok)' : c.class_label === 'B' ? 'var(--samurai-blue)' : 'var(--samurai-muted)', width: `${Math.min(c.value_pct, 100)}%` }}
                    />
                  </div>
                  <span style={{ width: '3rem', textAlign: 'right', fontSize: '0.72rem', fontWeight: 500, color: MUTED }}>{c.value_pct.toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dead & Slow-Moving Stock Analysis Hub */}
      <div className="sd-chart-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <h3 className="sd-chart-title" style={{ margin: 0 }}>Dead & Slow-Moving Stock Analysis</h3>
          <span className="sd-chip muted">P0 · dead-slow-stock-detector</span>
        </div>
        <p className="sd-chart-sub">
          SKUs with &gt;8 months inventory cover (90-day velocity) or zero movement in &gt;180 days. Ranked by total capital tied up.
        </p>
        {stats.deadSlowStock.length === 0 ? (
          <p style={{ color: MUTED, fontSize: '0.85rem' }}>No dead or slow-moving stock detected. Chotatsu (Procurement Agent) generates this from stock movement history.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">SKU & Item</Th>
                  <Th align="left">Category</Th>
                  <Th align="right">Qty</Th>
                  <Th align="right">Days No Movement</Th>
                  <Th align="right">Months Cover</Th>
                  <Th align="right">Tied-Up Value</Th>
                  <Th align="center">Flush Recommendation</Th>
                  <Th align="center">Action</Th>
                </tr>
              </thead>
              <tbody>
                {stats.deadSlowStock.map((d) => (
                  <tr key={d.sku} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="py-2">
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', fontWeight: 600, color: TEXT }}>{d.sku}</div>
                      <div style={{ fontSize: '0.72rem', color: MUTED }}>{d.item_name}</div>
                    </td>
                    <td className="py-2" style={{ color: MUTED }}>{d.category}</td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: TEXT }}>{d.current_qty.toLocaleString()}</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{d.days_since_last_movement}d</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{d.months_of_cover.toFixed(1)}</td>
                    <td className="py-2 text-right" style={{ color: 'var(--samurai-danger)', fontWeight: 700 }}>
                      <div style={{ fontSize: '0.65rem', color: MUTED, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>RM</div>
                      {d.total_tied_value >= 1_000_000
                        ? `${(d.total_tied_value / 1_000_000).toFixed(2)}M`
                        : d.total_tied_value >= 1_000
                          ? `${(d.total_tied_value / 1_000).toFixed(0)}K`
                          : d.total_tied_value.toLocaleString()}
                    </td>
                    <td className="py-2 text-center">
                      {d.action_recommendation === 'Bundle Promo with Top SKU' ? (
                        <span
                          className="sd-chip"
                          style={{
                            background: 'color-mix(in srgb, #8b5cf6 20%, transparent)',
                            color: '#a78bfa',
                            border: '1px solid color-mix(in srgb, #8b5cf6 40%, transparent)',
                            fontWeight: 600,
                          }}
                        >
                          Bundle Promo with Top SKU
                        </span>
                      ) : (
                        <span className={`sd-chip ${ACTION_STYLE[d.action_recommendation] ?? 'muted'}`}>
                          {d.action_recommendation}
                        </span>
                      )}
                    </td>
                    <td className="py-2 text-center">
                      <button
                        type="button"
                        onClick={() => {
                          setDeadStockTarget(d);
                          setSelectedComboStrategy('bundle_top_sku');
                          setCustomIdeaInput('');
                        }}
                        className="sd-btn sd-btn-secondary"
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}
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

      {/* Combination Sales Strategy Modal for Dead/Slow-Moving Stock */}
      {deadStockTarget && (
        <>
          <button
            type="button"
            style={{ position: 'fixed', inset: 0, zIndex: 40, background: 'rgba(0,0,0,0.4)', border: 'none', cursor: 'default' }}
            onClick={() => setDeadStockTarget(null)}
            aria-label="Close"
          />
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
            onClick={() => setDeadStockTarget(null)}
          >
            <div
              className="sd-card"
              style={{ position: 'relative', zIndex: 50, width: '100%', maxWidth: '32rem', height: 'fit-content', padding: '1.25rem' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.75rem', marginBottom: '0.75rem' }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: TEXT, margin: 0 }}>
                    Flush Strategy: Combination Sales
                  </h2>
                  <p style={{ fontSize: '0.72rem', color: MUTED, margin: 0 }}>
                    {deadStockTarget.item_name} ({deadStockTarget.sku}) · Tied Capital: RM {deadStockTarget.total_tied_value?.toLocaleString()}
                  </p>
                </div>
                <button type="button" className="sd-icon-btn" onClick={() => setDeadStockTarget(null)} aria-label="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: TEXT, marginBottom: '0.5rem' }}>
                  Select Sales Combination Strategy:
                </label>

                <div className="sd-stack" style={{ gap: '0.5rem' }}>
                  {/* Option 1 */}
                  <div
                    onClick={() => setSelectedComboStrategy('bundle_top_sku')}
                    style={{
                      padding: '0.65rem 0.85rem',
                      borderRadius: '0.5rem',
                      border: `1px solid ${selectedComboStrategy === 'bundle_top_sku' ? 'var(--samurai-lime)' : BORDER}`,
                      background: selectedComboStrategy === 'bundle_top_sku' ? 'var(--samurai-hover-ui)' : SURFACE_2,
                      cursor: 'pointer',
                      transition: 'border-color 150ms ease, background 150ms ease',
                    }}
                  >
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: selectedComboStrategy === 'bundle_top_sku' ? 'var(--samurai-lime)' : TEXT }}>
                      1. Bundle Promo with Top-Selling SKU
                    </div>
                    <div style={{ fontSize: '0.72rem', color: MUTED, marginTop: '0.15rem' }}>
                      Pair this slow-moving stock with a high-velocity Category A item at a 20% discount.
                    </div>
                  </div>

                  {/* Option 2 */}
                  <div
                    onClick={() => setSelectedComboStrategy('bogo_clearance')}
                    style={{
                      padding: '0.65rem 0.85rem',
                      borderRadius: '0.5rem',
                      border: `1px solid ${selectedComboStrategy === 'bogo_clearance' ? 'var(--samurai-lime)' : BORDER}`,
                      background: selectedComboStrategy === 'bogo_clearance' ? 'var(--samurai-hover-ui)' : SURFACE_2,
                      cursor: 'pointer',
                      transition: 'border-color 150ms ease, background 150ms ease',
                    }}
                  >
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: selectedComboStrategy === 'bogo_clearance' ? 'var(--samurai-lime)' : TEXT }}>
                      2. Buy 1 Get 1 Free (BOGO) Clearance
                    </div>
                    <div style={{ fontSize: '0.72rem', color: MUTED, marginTop: '0.15rem' }}>
                      Run an instant BOGO clearance push to double stock turnover velocity.
                    </div>
                  </div>

                  {/* Option 3 */}
                  <div
                    onClick={() => setSelectedComboStrategy('bulk_vendor_liquidation')}
                    style={{
                      padding: '0.65rem 0.85rem',
                      borderRadius: '0.5rem',
                      border: `1px solid ${selectedComboStrategy === 'bulk_vendor_liquidation' ? 'var(--samurai-lime)' : BORDER}`,
                      background: selectedComboStrategy === 'bulk_vendor_liquidation' ? 'var(--samurai-hover-ui)' : SURFACE_2,
                      cursor: 'pointer',
                      transition: 'border-color 150ms ease, background 150ms ease',
                    }}
                  >
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: selectedComboStrategy === 'bulk_vendor_liquidation' ? 'var(--samurai-lime)' : TEXT }}>
                      3. Bulk Wholesale Liquidation to Secondary Vendor
                    </div>
                    <div style={{ fontSize: '0.72rem', color: MUTED, marginTop: '0.15rem' }}>
                      Offload remaining batch to secondary liquidation vendor at 40% off cost.
                    </div>
                  </div>

                  {/* Option 4: Custom Idea */}
                  <div
                    onClick={() => setSelectedComboStrategy('custom_idea')}
                    style={{
                      padding: '0.65rem 0.85rem',
                      borderRadius: '0.5rem',
                      border: `1px solid ${selectedComboStrategy === 'custom_idea' ? 'var(--samurai-lime)' : BORDER}`,
                      background: selectedComboStrategy === 'custom_idea' ? 'var(--samurai-hover-ui)' : SURFACE_2,
                      cursor: 'pointer',
                      transition: 'border-color 150ms ease, background 150ms ease',
                    }}
                  >
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: selectedComboStrategy === 'custom_idea' ? 'var(--samurai-lime)' : TEXT }}>
                      4. Type Custom Strategy / Idea
                    </div>
                    <div style={{ fontSize: '0.72rem', color: MUTED, marginTop: '0.15rem', marginBottom: selectedComboStrategy === 'custom_idea' ? '0.4rem' : '0' }}>
                      Specify your own sales combination idea for Chotatsu (Procurement Agent).
                    </div>
                    {selectedComboStrategy === 'custom_idea' && (
                      <textarea
                        value={customIdeaInput}
                        onChange={(e) => setCustomIdeaInput(e.target.value)}
                        placeholder="e.g. Bundle with Q4 Corporate Gift Box and offer 15% instant rebate..."
                        rows={2}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          width: '100%',
                          borderRadius: '0.4rem',
                          border: `1px solid ${BORDER}`,
                          background: 'var(--samurai-surface)',
                          padding: '0.4rem 0.6rem',
                          fontSize: '0.8rem',
                          color: TEXT,
                          fontFamily: 'var(--font-body)',
                        }}
                      />
                    )}
                  </div>
                </div>
              </div>

              <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: '0.75rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setDeadStockTarget(null)}
                  className="sd-btn sd-btn-secondary"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const strategyText =
                      selectedComboStrategy === 'bundle_top_sku' ? 'Bundle Promo with Top-Selling SKU'
                      : selectedComboStrategy === 'bogo_clearance' ? 'Buy 1 Get 1 Free (BOGO) Clearance'
                      : selectedComboStrategy === 'bulk_vendor_liquidation' ? 'Bulk Wholesale Liquidation to Secondary Vendor'
                      : customIdeaInput || 'Custom Sales Combination Strategy';

                    onAction?.('trigger_liquidation', { ...deadStockTarget, combination_strategy: strategyText });
                    setDeadStockTarget(null);
                  }}
                  className="sd-btn sd-btn-primary"
                  style={{ padding: '0.4rem 0.9rem', fontSize: '0.75rem' }}
                >
                  Confirm & Dispatch Strategy
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

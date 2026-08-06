import { BarChart, PieChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';

interface Props { stats: CeoDashboardStats; color: string }

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;

function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function DealsDeepDiveTab({ stats, color }: Props) {
  const priorityData = stats.byPriority.map((p) => ({
    name: p.priority,
    value: p.count,
  }));

  const PRODUCT_SORT_ORDER = ['Apparel & Fashion', 'Consumer Electronics', 'Corporate Wholesale', 'Lifestyle & Home'];

  const sortedProducts = [...stats.byProduct].sort((a, b) => {
    const idxA = PRODUCT_SORT_ORDER.indexOf(a.product);
    const idxB = PRODUCT_SORT_ORDER.indexOf(b.product);
    if (idxA !== -1 && idxB !== -1) return idxA - idxB;
    if (idxA !== -1) return -1;
    if (idxB !== -1) return 1;
    return b.count - a.count;
  });

  const productData = sortedProducts.map((p) => ({
    name: `${p.product} (${p.count})`,
    value: p.count,
  }));

  return (
    <div className="sd-stack">
      <div className="sd-row">
        <div className="sd-chart-card !p-4">
          <h3 className="sd-chart-title !text-xs !font-bold">Deal Priority</h3>
          <p className="sd-chart-sub !text-[11px]">Open deals grouped by priority</p>
          <PieChart data={priorityData} color={color} unit="" height={170} innerRadius={30} outerRadius={52} legendFontSize="11px" />
        </div>
        <div className="sd-chart-card !p-4">
          <h3 className="sd-chart-title !text-xs !font-bold">Product Breakdown</h3>
          <p className="sd-chart-sub !text-[11px]">Open deals grouped by product category</p>
          <PieChart data={productData} color={color} unit="" height={170} innerRadius={30} outerRadius={52} legendFontSize="11px" />
        </div>
      </div>

      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Product Pipeline Value</h3>
        <p className="sd-chart-sub">Pipeline value by product</p>
        <BarChart
          data={sortedProducts}
          xKey="product"
          yKey="value"
          color={color}
          unit="RM "
          height={200}
        />
      </div>

      {/* Top deals table */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Top {stats.topDeals.length} Deals</h3>
        <p className="sd-chart-sub">Largest open opportunities</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                <Th align="left">Deal</Th>
                <Th align="left">Customer</Th>
                <Th align="left">Owner</Th>
                <Th align="left">Stage</Th>
                <Th align="right">Amount</Th>
                <Th align="center">Hot</Th>
              </tr>
            </thead>
            <tbody>
              {stats.topDeals.slice(0, 10).map((deal, i) => (
                <tr key={deal.slug} style={{ borderBottom: `1px solid ${BORDER}`, background: i % 2 === 1 ? SURFACE_2 : undefined }}>
                  <td className="px-3 py-2.5 max-w-[180px] truncate" style={{ fontWeight: 600, color: TEXT }} title={deal.title}>
                    {deal.title}
                  </td>
                  <td className="px-3 py-2.5" style={{ color: MUTED }}>{deal.customer}</td>
                  <td className="px-3 py-2.5" style={{ color: MUTED }}>{deal.owner}</td>
                  <td className="px-3 py-2.5">
                    <span className="sd-chip muted">{deal.stage}</span>
                  </td>
                  <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: TEXT }}>
                    RM {(deal.amount / 1000).toFixed(0)}K
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    {deal.hot ? (
                      <span className="inline-block h-2 w-2 rounded-full" style={{ background: 'var(--samurai-danger)' }} title="Hot" />
                    ) : deal.priority === 'Warm' ? (
                      <span className="inline-block h-2 w-2 rounded-full" style={{ background: 'var(--samurai-warning)' }} title="Warm" />
                    ) : (
                      <span className="inline-block h-2 w-2 rounded-full" style={{ background: 'var(--samurai-muted)' }} title="Cold" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

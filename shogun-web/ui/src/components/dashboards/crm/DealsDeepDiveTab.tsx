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

  const productData = stats.byProduct.map((p) => ({
    name: p.product,
    value: p.count,
  }));

  return (
    <div className="sd-stack">
      <div className="sd-row">
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Deal Priority</h3>
          <p className="sd-chart-sub">Open deals grouped by priority</p>
          <PieChart data={priorityData} color={color} unit="" height={220} innerRadius={45} />
        </div>
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Product Breakdown</h3>
          <p className="sd-chart-sub">Open deals grouped by product</p>
          <PieChart data={productData} color={color} unit="" height={220} innerRadius={45} />
        </div>
      </div>

      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Product Pipeline Value</h3>
        <p className="sd-chart-sub">Pipeline value by product</p>
        <BarChart
          data={stats.byProduct}
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

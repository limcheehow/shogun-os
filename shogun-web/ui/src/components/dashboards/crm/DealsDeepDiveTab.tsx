import { BarChart, PieChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';

interface Props { stats: CeoDashboardStats; color: string }

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
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Deal Priority</h3>
          <PieChart data={priorityData} color={color} unit="" height={220} innerRadius={45} />
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Product Breakdown</h3>
          <PieChart data={productData} color={color} unit="" height={220} innerRadius={45} />
        </div>
      </div>

      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Product Pipeline Value</h3>
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
      <div className="card overflow-hidden">
        <div className="border-b border-surface-border px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-700">Top {stats.topDeals.length} Deals</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2">Deal</th>
                <th className="px-4 py-2">Customer</th>
                <th className="px-4 py-2">Owner</th>
                <th className="px-4 py-2">Stage</th>
                <th className="px-4 py-2 text-right">Amount</th>
                <th className="px-4 py-2 text-center">Hot</th>
              </tr>
            </thead>
            <tbody>
              {stats.topDeals.slice(0, 10).map((deal) => (
                <tr key={deal.slug} className="border-b border-surface-border last:border-0 hover:bg-slate-50">
                  <td className="max-w-[180px] truncate px-4 py-2 font-medium text-slate-900" title={deal.title}>
                    {deal.title}
                  </td>
                  <td className="px-4 py-2 text-slate-600">{deal.customer}</td>
                  <td className="px-4 py-2 text-slate-600">{deal.owner}</td>
                  <td className="px-4 py-2">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {deal.stage}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-medium text-slate-900">
                    RM {(deal.amount / 1000).toFixed(0)}K
                  </td>
                  <td className="px-4 py-2 text-center">
                    {deal.hot ? (
                      <span className="inline-block h-2 w-2 rounded-full bg-red-500" title="Hot" />
                    ) : deal.priority === 'Warm' ? (
                      <span className="inline-block h-2 w-2 rounded-full bg-amber-400" title="Warm" />
                    ) : (
                      <span className="inline-block h-2 w-2 rounded-full bg-slate-300" title="Cold" />
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
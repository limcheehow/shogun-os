import { BarChart, LineChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';

interface Props { stats: CeoDashboardStats; color: string }

export function SalesPulseTab({ stats, color }: Props) {
  const KPIs = [
    { label: 'Sales MTD', value: `RM ${(stats.salesMTD / 1000).toFixed(0)}K` },
    { label: 'Sales QTD', value: `RM ${(stats.salesQTD / 1000).toFixed(0)}K` },
    { label: 'Sales YTD', value: `RM ${(stats.salesYTD / 1000).toFixed(0)}K` },
    { label: 'Win Rate', value: `${stats.winRate}%` },
    { label: 'Avg Deal', value: `RM ${(stats.avgDealSize / 1000).toFixed(0)}K` },
    { label: 'Active Deals', value: stats.totalActiveDeals.toString() },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {KPIs.map((kpi) => (
          <div key={kpi.label} className="card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{kpi.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900">{kpi.value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Sales by Manager (YTD)</h3>
          <BarChart
            data={stats.byManager}
            xKey="owner"
            yKey="salesYTD"
            color={color}
            unit="RM "
            height={220}
          />
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Monthly Sales Trend</h3>
          <LineChart
            data={stats.wonByMonth}
            xKey="month"
            yKey="value"
            color={color}
            unit="RM "
            height={220}
          />
        </div>
      </div>
    </div>
  );
}
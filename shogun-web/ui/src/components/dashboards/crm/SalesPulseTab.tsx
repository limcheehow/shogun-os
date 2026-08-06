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
    <div className="sd-stack">
      <div className="sd-kpi-grid">
        {KPIs.map((kpi) => (
          <div key={kpi.label} className="sd-kpi-card">
            <div className="sd-kpi-label">{kpi.label}</div>
            <div className="sd-kpi-value">{kpi.value}</div>
          </div>
        ))}
      </div>

      <div className="sd-row">
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Sales by Manager (YTD)</h3>
          <p className="sd-chart-sub">Year-to-date sales by owner</p>
          <BarChart
            data={stats.byManager}
            xKey="owner"
            yKey="salesYTD"
            color={color}
            unit="RM "
            height={220}
          />
        </div>
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Monthly Sales Trend</h3>
          <p className="sd-chart-sub">Closed-won revenue by month</p>
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

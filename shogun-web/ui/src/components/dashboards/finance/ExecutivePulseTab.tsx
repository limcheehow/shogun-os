import { AlertTriangle, TrendingDown, TrendingUp } from 'lucide-react';
import { ComboChart, LineChart } from '../charts';
import type { FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmt = (n: number) =>
  n >= 1_000_000
    ? `RM ${(n / 1_000_000).toFixed(2)}M`
    : n >= 1_000
      ? `RM ${(n / 1_000).toFixed(0)}K`
      : `RM ${n.toFixed(0)}`;

const RUNWAY_BADGE: Record<string, { label: string; cls: string }> = {
  healthy: { label: 'Healthy', cls: 'bg-emerald-100 text-emerald-700' },
  caution: { label: 'Caution', cls: 'bg-amber-100 text-amber-700' },
  critical: { label: 'Critical', cls: 'bg-rose-100 text-rose-700' },
  unknown:  { label: '—', cls: 'bg-slate-100 text-slate-500' },
};

export function ExecutivePulseTab({ stats, color }: Props) {
  const badge = RUNWAY_BADGE[stats.runwayStatus] ?? RUNWAY_BADGE.unknown;

  const KPIs = [
    { label: 'Total Liquid Cash', value: fmt(stats.totalLiquidCash) },
    { label: 'Net Monthly Burn', value: fmt(stats.netMonthlyBurn) },
    {
      label: 'Cash Runway',
      value: stats.cashRunwayMonths > 0 ? `${stats.cashRunwayMonths.toFixed(1)} mo` : '—',
      badge: badge,
    },
    { label: 'Revenue MTD', value: fmt(stats.revenueMTD) },
    { label: 'Gross Margin', value: `${stats.grossMargin.toFixed(1)}%` },
    { label: 'EBITDA Margin', value: `${stats.ebitdaMargin.toFixed(1)}%` },
  ];

  const COMBO_SERIES = [
    { key: 'revenue', label: 'Revenue', type: 'bar' as const, color },
    { key: 'opex',    label: 'OPEX',    type: 'line' as const, color: '#f59e0b' },
    { key: 'net',     label: 'Net',     type: 'line' as const, color: '#6366f1' },
  ];

  const ALERT_ICON: Record<string, typeof TrendingDown> = {
    concentration: TrendingUp,
    overrun: TrendingDown,
    ar_overdue: AlertTriangle,
  };

  return (
    <div className="space-y-4">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {KPIs.map((kpi) => (
          <div key={kpi.label} className="card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{kpi.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900">{kpi.value}</div>
            {kpi.badge && (
              <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${kpi.badge.cls}`}>
                {kpi.badge.label}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Risk Alert Banner */}
      {stats.riskAlerts.length > 0 && (
        <div className="space-y-2">
          {stats.riskAlerts.map((alert, i) => {
            const Icon = ALERT_ICON[alert.type] ?? AlertTriangle;
            const cls = alert.level === 'critical'
              ? 'border-rose-200 bg-rose-50 text-rose-700'
              : 'border-amber-200 bg-amber-50 text-amber-700';
            return (
              <div key={i} className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium ${cls}`}>
                <Icon className="h-4 w-4 shrink-0" />
                {alert.message}
              </div>
            );
          })}
        </div>
      )}

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Revenue vs OPEX vs Net Profit (12 Mo)</h3>
          <ComboChart
            data={stats.revenueOpexTrend}
            xKey="month"
            series={COMBO_SERIES}
            unit="RM "
            height={220}
          />
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Cash Balance & Net Flow Trend</h3>
          <LineChart
            data={stats.cashFlowTrend}
            xKey="month"
            yKey="cash"
            color={color}
            unit="RM "
            height={220}
            dataKeys={['cash', 'netFlow']}
            colors={[color, '#94a3b8']}
            labels={{ cash: 'Cash Balance', netFlow: 'Net Cash Flow' }}
          />
        </div>
      </div>

      {/* Statutory Liabilities Footer */}
      {stats.unpaidStatutory > 0 && (
        <div className="card flex items-center justify-between px-5 py-3">
          <span className="text-sm font-medium text-slate-600">Unpaid Statutory & Tax Liabilities</span>
          <span className="text-base font-bold text-rose-600">{fmt(stats.unpaidStatutory)}</span>
        </div>
      )}
    </div>
  );
}

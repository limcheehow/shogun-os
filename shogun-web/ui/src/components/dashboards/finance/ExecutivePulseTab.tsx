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

const RUNWAY_CHIP: Record<string, { label: string; cls: string }> = {
  healthy:  { label: 'Healthy',  cls: 'ok' },
  caution:  { label: 'Caution',  cls: 'warn' },
  critical: { label: 'Critical', cls: 'bad' },
  unknown:   { label: '—',        cls: 'muted' },
};

export function ExecutivePulseTab({ stats, color }: Props) {
  const chip = RUNWAY_CHIP[stats.runwayStatus] ?? RUNWAY_CHIP.unknown;

  const KPIs = [
    { label: 'Total Liquid Cash', value: fmt(stats.totalLiquidCash) },
    { label: 'Net Monthly Burn', value: fmt(stats.netMonthlyBurn) },
    {
      label: 'Cash Runway',
      value: stats.cashRunwayMonths > 0 ? `${stats.cashRunwayMonths.toFixed(1)} mo` : '—',
      chip,
    },
    { label: 'Revenue MTD', value: fmt(stats.revenueMTD) },
    { label: 'Gross Margin', value: `${stats.grossMargin.toFixed(1)}%` },
    { label: 'EBITDA Margin', value: `${stats.ebitdaMargin.toFixed(1)}%` },
  ];

  const COMBO_SERIES = [
    { key: 'revenue', label: 'Revenue', type: 'bar' as const, color },
    { key: 'opex',    label: 'OPEX',    type: 'line' as const, color: '#fbbf24' },
    { key: 'net',     label: 'Net',     type: 'line' as const, color: '#ceef7d' },
  ];

  const ALERT_ICON: Record<string, typeof TrendingDown> = {
    concentration: TrendingUp,
    overrun: TrendingDown,
    ar_overdue: AlertTriangle,
  };

  return (
    <div className="sd-stack">
      <div className="sd-kpi-grid">
        {KPIs.map((kpi) => (
          <div key={kpi.label} className="sd-kpi-card">
            <div className="sd-kpi-label">{kpi.label}</div>
            <div className="sd-kpi-value">{kpi.value}</div>
            {kpi.chip && (
              <div className="sd-kpi-sub">
                <span className={`sd-chip ${kpi.chip.cls}`}>{kpi.chip.label}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {stats.riskAlerts.length > 0 && (
        <div className="sd-stack" style={{ gap: '0.5rem' }}>
          {stats.riskAlerts.map((alert, i) => {
            const Icon = ALERT_ICON[alert.type] ?? AlertTriangle;
            return (
              <div key={i} className={`sd-alert-row ${alert.level === 'critical' ? 'critical' : 'warning'}`}>
                <Icon className="h-4 w-4 shrink-0" />
                {alert.message}
              </div>
            );
          })}
        </div>
      )}

      <div className="sd-row">
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Revenue vs OPEX vs Net Profit (12 Mo)</h3>
          <p className="sd-chart-sub">Monthly revenue, operating expenditure, and net result</p>
          <ComboChart data={stats.revenueOpexTrend} xKey="month" series={COMBO_SERIES} unit="RM " height={220} />
        </div>
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Cash Balance & Net Flow Trend</h3>
          <p className="sd-chart-sub">Liquidity movement across the reporting window</p>
          <LineChart
            data={stats.cashFlowTrend}
            xKey="month"
            yKey="cash"
            color={color}
            unit="RM "
            height={220}
            dataKeys={['cash', 'netFlow']}
            colors={[color, '#ceef7d']}
            labels={{ cash: 'Cash Balance', netFlow: 'Net Cash Flow' }}
          />
        </div>
      </div>

      {stats.unpaidStatutory > 0 && (
        <div className="sd-chart-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--samurai-muted)' }}>Unpaid Statutory & Tax Liabilities</span>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--samurai-danger)' }}>{fmt(stats.unpaidStatutory)}</span>
        </div>
      )}
    </div>
  );
}
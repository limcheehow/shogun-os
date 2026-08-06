import { BarChart, FunnelChart, LineChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';
import { chartColors } from '../../../lib/palette';

interface Props { stats: CeoDashboardStats; color: string }

export function PipelineForecastTab({ stats, color }: Props) {
  const multiColors = chartColors(color, 3);

  const KPIs = [
    { label: 'Total Pipeline', value: `RM ${(stats.totalPipelineValue / 1000).toFixed(0)}K` },
    { label: 'Weighted', value: `RM ${(stats.weightedPipelineValue / 1000).toFixed(0)}K` },
    { label: 'Coverage Ratio', value: `${stats.pipelineCoverage}x` },
    { label: 'Cycle (avg)', value: `${stats.salesCycleDays}d` },
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
          <h3 className="sd-chart-title">Sales Funnel</h3>
          <p className="sd-chart-sub">Deal count and value by stage</p>
          <FunnelChart data={stats.byStage} color={color} unit="RM " height={300} />
        </div>
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Monthly Pipeline (Active + Won)</h3>
          <p className="sd-chart-sub">Pipeline movement across months</p>
          <LineChart
            data={stats.byMonth}
            xKey="month"
            yKey="value"
            color={color}
            unit="RM "
            height={300}
          />
        </div>
      </div>

      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Manager Comparison</h3>
        <p className="sd-chart-sub">Pipeline value vs weighted pipeline by manager</p>
        <BarChart
          data={stats.byManager}
          xKey="owner"
          yKey="pipelineValue"
          color={color}
          unit="RM "
          height={200}
          dataKeys={['pipelineValue', 'weightedPipeline']}
          colors={multiColors}
        />
      </div>
    </div>
  );
}

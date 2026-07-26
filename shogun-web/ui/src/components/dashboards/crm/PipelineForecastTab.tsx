import { BarChart, FunnelChart, LineChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';
import { chartColors } from '../../../lib/palette';

interface Props { stats: CeoDashboardStats; color: string }

export function PipelineForecastTab({ stats, color }: Props) {
  const multiColors = chartColors(color, 3);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="card p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Total Pipeline</div>
          <div className="mt-1 text-xl font-bold text-slate-900">RM {(stats.totalPipelineValue / 1000).toFixed(0)}K</div>
        </div>
        <div className="card p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Weighted</div>
          <div className="mt-1 text-xl font-bold text-slate-900">RM {(stats.weightedPipelineValue / 1000).toFixed(0)}K</div>
        </div>
        <div className="card p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Coverage Ratio</div>
          <div className="mt-1 text-xl font-bold text-slate-900">{stats.pipelineCoverage}x</div>
        </div>
        <div className="card p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Cycle (avg)</div>
          <div className="mt-1 text-xl font-bold text-slate-900">{stats.salesCycleDays}d</div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Sales Funnel</h3>
          <FunnelChart data={stats.byStage} color={color} unit="RM " height={300} />
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Monthly Pipeline (Active + Won)</h3>
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

      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Manager Comparison</h3>
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
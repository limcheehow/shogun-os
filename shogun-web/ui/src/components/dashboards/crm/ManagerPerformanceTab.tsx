import { BarChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';

interface Props {
  stats: CeoDashboardStats;
  color: string;
  onDrillDown: (owner: string) => void;
}

export function ManagerPerformanceTab({ stats, color, onDrillDown }: Props) {
  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Manager Sales YTD</h3>
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
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Manager Comparison</h3>
        <BarChart
          data={stats.byManager}
          xKey="owner"
          yKey="deals"
          color={color}
          height={200}
        />
      </div>

      {/* Manager table */}
      <div className="card overflow-hidden">
        <div className="border-b border-surface-border px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-700">Manager Details</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2">Owner</th>
                <th className="px-4 py-2 text-right">Pipeline</th>
                <th className="px-4 py-2 text-right">Weighted</th>
                <th className="px-4 py-2 text-right">Deals</th>
                <th className="px-4 py-2 text-right">Won</th>
                <th className="px-4 py-2 text-right">Win Rate</th>
                <th className="px-4 py-2 text-right">YTD</th>
              </tr>
            </thead>
            <tbody>
              {stats.byManager.map((m) => (
                <tr
                  key={m.owner}
                  className="cursor-pointer border-b border-surface-border last:border-0 hover:bg-slate-50"
                  onClick={() => onDrillDown(m.owner)}
                >
                  <td className="px-4 py-2 font-medium text-slate-900">{m.owner}</td>
                  <td className="px-4 py-2 text-right text-slate-700">RM {(m.pipelineValue / 1000).toFixed(0)}K</td>
                  <td className="px-4 py-2 text-right text-slate-700">RM {(m.weightedPipeline / 1000).toFixed(0)}K</td>
                  <td className="px-4 py-2 text-right text-slate-700">{m.deals}</td>
                  <td className="px-4 py-2 text-right text-slate-700">{m.wonDeals}</td>
                  <td className="px-4 py-2 text-right text-slate-700">{m.winRate}%</td>
                  <td className="px-4 py-2 text-right font-semibold text-slate-900">RM {(m.salesYTD / 1000).toFixed(0)}K</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* At-risk alerts */}
      {stats.atRiskByManager.length > 0 && (
        <div className="card overflow-hidden">
          <div className="border-b border-surface-border px-4 py-3">
            <h3 className="text-sm font-semibold text-rose-700">At-Risk Deals (&gt;30 days stalled)</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs font-medium uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2">Owner</th>
                  <th className="px-4 py-2 text-right">Stalled Deals</th>
                  <th className="px-4 py-2 text-right">Value at Risk</th>
                </tr>
              </thead>
              <tbody>
                {stats.atRiskByManager.map((r) => (
                  <tr key={r.owner} className="border-b border-surface-border last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-2 font-medium text-slate-900">{r.owner}</td>
                    <td className="px-4 py-2 text-right text-rose-600">{r.atRiskDeals}</td>
                    <td className="px-4 py-2 text-right text-rose-600">RM {(r.atRiskValue / 1000).toFixed(0)}K</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
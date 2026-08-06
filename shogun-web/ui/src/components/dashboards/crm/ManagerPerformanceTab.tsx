import { BarChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';

interface Props {
  stats: CeoDashboardStats;
  color: string;
  onDrillDown: (owner: string) => void;
}

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;

function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function ManagerPerformanceTab({ stats, color, onDrillDown }: Props) {
  return (
    <div className="sd-stack">
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Manager Sales YTD</h3>
        <p className="sd-chart-sub">Year-to-date sales by manager</p>
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
        <h3 className="sd-chart-title">Manager Comparison</h3>
        <p className="sd-chart-sub">Deal counts by manager</p>
        <BarChart
          data={stats.byManager}
          xKey="owner"
          yKey="deals"
          color={color}
          height={200}
        />
      </div>

      {/* Manager table */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Manager Details</h3>
        <p className="sd-chart-sub">Click a row for drill-down</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                <Th align="left">Owner</Th>
                <Th align="right">Pipeline</Th>
                <Th align="right">Weighted</Th>
                <Th align="right">Deals</Th>
                <Th align="right">Won</Th>
                <Th align="right">Win Rate</Th>
                <Th align="right">YTD</Th>
              </tr>
            </thead>
            <tbody>
              {stats.byManager.map((m, i) => (
                <tr
                  key={m.owner}
                  className="cursor-pointer"
                  style={{ borderBottom: `1px solid ${BORDER}`, background: i % 2 === 1 ? SURFACE_2 : undefined }}
                  onClick={() => onDrillDown(m.owner)}
                >
                  <td className="px-3 py-2.5" style={{ fontWeight: 600, color: TEXT }}>{m.owner}</td>
                  <td className="px-3 py-2.5 text-right" style={{ color: TEXT }}>RM {(m.pipelineValue / 1000).toFixed(0)}K</td>
                  <td className="px-3 py-2.5 text-right" style={{ color: TEXT }}>RM {(m.weightedPipeline / 1000).toFixed(0)}K</td>
                  <td className="px-3 py-2.5 text-right" style={{ color: TEXT }}>{m.deals}</td>
                  <td className="px-3 py-2.5 text-right" style={{ color: TEXT }}>{m.wonDeals}</td>
                  <td className="px-3 py-2.5 text-right" style={{ color: TEXT }}>{m.winRate}%</td>
                  <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: TEXT }}>RM {(m.salesYTD / 1000).toFixed(0)}K</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* At-risk alerts */}
      {stats.atRiskByManager.length > 0 && (
        <div className="sd-chart-card">
          <h3 className="sd-chart-title" style={{ color: 'var(--samurai-danger)' }}>At-Risk Deals (&gt;30 days stalled)</h3>
          <p className="sd-chart-sub">Stalled deal value by manager</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Owner</Th>
                  <Th align="right">Stalled Deals</Th>
                  <Th align="right">Value at Risk</Th>
                </tr>
              </thead>
              <tbody>
                {stats.atRiskByManager.map((r, i) => (
                  <tr key={r.owner} style={{ borderBottom: `1px solid ${BORDER}`, background: i % 2 === 1 ? SURFACE_2 : undefined }}>
                    <td className="px-3 py-2.5" style={{ fontWeight: 600, color: TEXT }}>{r.owner}</td>
                    <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: 'var(--samurai-danger)' }}>{r.atRiskDeals}</td>
                    <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: 'var(--samurai-danger)' }}>RM {(r.atRiskValue / 1000).toFixed(0)}K</td>
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

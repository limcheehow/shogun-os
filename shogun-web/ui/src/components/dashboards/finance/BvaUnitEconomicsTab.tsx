import { BarChart } from '../charts';
import type { FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmtMyr = (n: number) =>
  n >= 1_000_000 ? `RM ${(n / 1_000_000).toFixed(2)}M` : `RM ${(n / 1_000).toFixed(0)}K`;

export function BvaUnitEconomicsTab({ stats, color }: Props) {
  const ue = stats.unitEconomics;

  return (
    <div className="space-y-4">
      {/* BvA Chart */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Departmental Budget vs Actual Spend (YTD)</h3>
        <BarChart
          data={stats.bvaDepartments}
          xKey="department"
          yKey="actual_ytd"
          color={color}
          unit="RM "
          height={220}
          dataKeys={['budget_ytd', 'actual_ytd']}
          colors={['#cbd5e1', color]}
        />
      </div>

      {/* BvA Variance Table */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Departmental Variance Detail</h3>
        {stats.bvaDepartments.length === 0 ? (
          <p className="text-sm text-slate-400">No budget data available yet. Finance Agent (Koku) generates this from budget.json.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">Department</th>
                  <th className="pb-2 text-right font-medium">YTD Budget</th>
                  <th className="pb-2 text-right font-medium">YTD Actual</th>
                  <th className="pb-2 text-right font-medium">Variance</th>
                  <th className="pb-2 text-right font-medium">Var %</th>
                  <th className="pb-2 text-center font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.bvaDepartments.map((dept) => (
                  <tr key={dept.department} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-medium text-slate-800">{dept.department}</td>
                    <td className="py-2 text-right text-slate-700">{fmtMyr(dept.budget_ytd)}</td>
                    <td className="py-2 text-right text-slate-700">{fmtMyr(dept.actual_ytd)}</td>
                    <td className={`py-2 text-right font-semibold ${dept.variance > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {dept.variance > 0 ? '+' : ''}{fmtMyr(dept.variance)}
                    </td>
                    <td className={`py-2 text-right font-semibold ${dept.variance_pct > 10 ? 'text-rose-600' : 'text-slate-700'}`}>
                      {dept.variance_pct > 0 ? '+' : ''}{dept.variance_pct.toFixed(1)}%
                    </td>
                    <td className="py-2 text-center">
                      {dept.variance_pct > 10 ? (
                        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">⚠ Overrun</span>
                      ) : dept.variance_pct < 0 ? (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">✓ Under Budget</span>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">On Track</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Unit Economics & Client Concentration */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Unit Economics */}
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Unit Economics</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Gross Margin', value: `${ue.gross_margin_pct.toFixed(1)}%` },
              { label: 'Contribution Margin', value: `${ue.contribution_margin_pct.toFixed(1)}%` },
              { label: 'CAC', value: ue.cac > 0 ? fmtMyr(ue.cac) : '—' },
              { label: 'LTV', value: ue.ltv > 0 ? fmtMyr(ue.ltv) : '—' },
              { label: 'LTV/CAC Ratio', value: ue.ltv_cac_ratio > 0 ? `${ue.ltv_cac_ratio.toFixed(1)}x` : '—' },
            ].map((m) => (
              <div key={m.label} className="rounded-lg bg-surface-muted p-3">
                <div className="text-xs font-medium text-slate-500">{m.label}</div>
                <div className="mt-1 text-lg font-bold text-slate-900">{m.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Client Concentration */}
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Revenue Concentration</h3>
          {stats.clientConcentration.length === 0 ? (
            <p className="text-sm text-slate-400">No concentration data available yet.</p>
          ) : (
            <div className="space-y-2">
              {stats.clientConcentration.slice(0, 8).map((client) => (
                <div key={client.name} className="flex items-center gap-3">
                  <div className="min-w-0 flex-1 truncate text-xs font-medium text-slate-700">{client.name}</div>
                  <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-2 rounded-full ${client.revenue_pct > 20 ? 'bg-rose-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(client.revenue_pct, 100)}%` }}
                    />
                  </div>
                  <div className={`w-10 text-right text-xs font-semibold ${client.revenue_pct > 20 ? 'text-rose-600' : 'text-slate-700'}`}>
                    {client.revenue_pct.toFixed(1)}%
                  </div>
                  {client.revenue_pct > 20 && (
                    <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-xs font-semibold text-rose-700">⚠</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

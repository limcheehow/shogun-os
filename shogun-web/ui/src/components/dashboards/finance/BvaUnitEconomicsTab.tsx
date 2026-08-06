import { BarChart } from '../charts';
import type { FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmtMyr = (n: number) =>
  n >= 1_000_000 ? `RM ${(n / 1_000_000).toFixed(2)}M` : `RM ${(n / 1_000).toFixed(0)}K`;

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;

function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="pb-2" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function BvaUnitEconomicsTab({ stats, color }: Props) {
  const ue = stats.unitEconomics;

  return (
    <div className="sd-stack">
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Departmental Budget vs Actual Spend (YTD)</h3>
        <p className="sd-chart-sub">Budget vs actual across departments</p>
        <BarChart
          data={stats.bvaDepartments}
          xKey="department"
          yKey="actual_ytd"
          color={color}
          unit="RM "
          height={220}
          dataKeys={['budget_ytd', 'actual_ytd']}
          colors={['var(--samurai-muted)', color]}
        />
      </div>

      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Departmental Variance Detail</h3>
        <p className="sd-chart-sub">Flags overruns above 10%</p>
        {stats.bvaDepartments.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: MUTED }}>No budget data available yet. Finance Agent (Koku) generates this from budget.json.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Department</Th>
                  <Th align="right">YTD Budget</Th>
                  <Th align="right">YTD Actual</Th>
                  <Th align="right">Variance</Th>
                  <Th align="right">Var %</Th>
                  <Th align="center">Status</Th>
                </tr>
              </thead>
              <tbody>
                {stats.bvaDepartments.map((dept) => (
                  <tr key={dept.department} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="py-2" style={{ fontWeight: 600, color: TEXT }}>{dept.department}</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{fmtMyr(dept.budget_ytd)}</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{fmtMyr(dept.actual_ytd)}</td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: dept.variance > 0 ? 'var(--samurai-danger)' : 'var(--samurai-ok)' }}>
                      {dept.variance > 0 ? '+' : ''}{fmtMyr(dept.variance)}
                    </td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: dept.variance_pct > 10 ? 'var(--samurai-danger)' : TEXT }}>
                      {dept.variance_pct > 0 ? '+' : ''}{dept.variance_pct.toFixed(1)}%
                    </td>
                    <td className="py-2 text-center">
                      {dept.variance_pct > 10 ? (
                        <span className="sd-chip bad">⚠ Overrun</span>
                      ) : dept.variance_pct < 0 ? (
                        <span className="sd-chip ok">✓ Under Budget</span>
                      ) : (
                        <span className="sd-chip muted">On Track</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="sd-row">
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Unit Economics</h3>
          <p className="sd-chart-sub">Margins, acquisition efficiency, and lifetime value</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
            {[
              { label: 'Gross Margin', value: `${ue.gross_margin_pct.toFixed(1)}%` },
              { label: 'Contribution Margin', value: `${ue.contribution_margin_pct.toFixed(1)}%` },
              { label: 'CAC', value: ue.cac > 0 ? fmtMyr(ue.cac) : '—' },
              { label: 'LTV', value: ue.ltv > 0 ? fmtMyr(ue.ltv) : '—' },
              { label: 'LTV/CAC Ratio', value: ue.ltv_cac_ratio > 0 ? `${ue.ltv_cac_ratio.toFixed(1)}x` : '—' },
            ].map((m) => (
              <div key={m.label} style={{ borderRadius: '0.5rem', background: SURFACE_2, padding: '0.6rem 0.75rem' }}>
                <div style={{ fontSize: '0.72rem', color: MUTED }}>{m.label}</div>
                <div style={{ marginTop: '0.2rem', fontFamily: 'var(--font-display)', fontSize: '1.05rem', fontWeight: 600, color: TEXT }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Revenue Concentration</h3>
          <p className="sd-chart-sub">Single-customer exposure (warn &gt; 20%)</p>
          {stats.clientConcentration.length === 0 ? (
            <p style={{ fontSize: '0.85rem', color: MUTED }}>No concentration data available yet.</p>
          ) : (
            <div className="sd-stack" style={{ gap: '0.5rem' }}>
              {stats.clientConcentration.slice(0, 8).map((client) => (
                <div key={client.name} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div style={{ minWidth: 0, flex: 1, fontSize: '0.75rem', fontWeight: 500, color: TEXT, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{client.name}</div>
                  <div style={{ height: '0.5rem', width: '6rem', borderRadius: 999, overflow: 'hidden', background: SURFACE_2 }}>
                    <div
                      style={{ height: '100%', borderRadius: 999, background: client.revenue_pct > 20 ? 'var(--samurai-danger)' : 'var(--samurai-ok)', width: `${Math.min(client.revenue_pct, 100)}%` }}
                    />
                  </div>
                  <div style={{ width: '2.5rem', textAlign: 'right', fontSize: '0.72rem', fontWeight: 600, color: client.revenue_pct > 20 ? 'var(--samurai-danger)' : TEXT }}>
                    {client.revenue_pct.toFixed(1)}%
                  </div>
                  {client.revenue_pct > 20 && <span className="sd-chip bad">⚠</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
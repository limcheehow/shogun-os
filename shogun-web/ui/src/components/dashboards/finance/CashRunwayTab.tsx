import { useState } from 'react';
import { LineChart } from '../charts';
import type { FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmtMyr = (n: number) =>
  n >= 1_000_000 ? `RM ${(n / 1_000_000).toFixed(2)}M` : `RM ${(n / 1_000).toFixed(0)}K`;

const SCENARIOS = ['conservative', 'expected', 'optimistic'] as const;
type Scenario = typeof SCENARIOS[number];

const SCENARIO_LABEL: Record<Scenario, string> = {
  conservative: 'Conservative',
  expected: 'Expected',
  optimistic: 'Optimistic',
};

const RUNWAY_CHIP: Record<string, { label: string; cls: string }> = {
  healthy:  { label: '✓ Healthy (>6 months)',  cls: 'ok' },
  caution:  { label: '⚠ Caution (3–6 months)', cls: 'warn' },
  critical: { label: '⛔ Critical (<3 months)', cls: 'bad' },
  unknown:   { label: 'Unknown',                cls: 'muted' },
};

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';

export function CashRunwayTab({ stats, color }: Props) {
  const [scenario, setScenario] = useState<Scenario>('expected');
  const forecastData = stats.forecast13w[scenario] ?? [];
  const totalBurn = stats.fixedOpex + stats.variableOpex;
  const fixedPct = totalBurn > 0 ? (stats.fixedOpex / totalBurn) * 100 : 0;
  const chip = RUNWAY_CHIP[stats.runwayStatus] ?? RUNWAY_CHIP.unknown;

  return (
    <div className="sd-stack">
      <div className="sd-row">
        <div className="sd-card">
          <div className="sd-kpi-label">Cash Runway</div>
          <div className="sd-kpi-value" style={{ fontSize: '2.2rem' }}>
            {stats.cashRunwayMonths > 0 ? stats.cashRunwayMonths.toFixed(1) : '—'}
            <span style={{ marginLeft: '0.4rem', fontSize: '0.95rem', fontWeight: 400, color: MUTED }}>months</span>
          </div>
          <div style={{ marginTop: '0.6rem' }}>
            <span className={`sd-chip ${chip.cls}`}>{chip.label}</span>
          </div>
          <div style={{ marginTop: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: MUTED, marginBottom: '0.3rem' }}>
              <span>Fixed OPEX (Payroll/Rent/Cloud)</span>
              <span style={{ fontWeight: 600, color: TEXT }}>{fmtMyr(stats.fixedOpex)}</span>
            </div>
            <div style={{ height: '0.5rem', borderRadius: 999, overflow: 'hidden', background: SURFACE_2 }}>
              <div style={{ height: '100%', width: `${fixedPct}%`, borderRadius: 999, background: 'var(--samurai-ok)' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: MUTED, marginTop: '0.6rem', marginBottom: '0.3rem' }}>
              <span>Variable OPEX (Mktg/Travel/Other)</span>
              <span style={{ fontWeight: 600, color: TEXT }}>{fmtMyr(stats.variableOpex)}</span>
            </div>
            <div style={{ height: '0.5rem', borderRadius: 999, overflow: 'hidden', background: SURFACE_2 }}>
              <div style={{ height: '100%', width: `${100 - fixedPct}%`, borderRadius: 999, background: 'var(--samurai-warning)' }} />
            </div>
          </div>
        </div>

        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Bank Accounts</h3>
          <p className="sd-chart-sub">Operating, payroll, tax reserve &amp; FX accounts</p>
          {stats.bankAccounts.length === 0 ? (
            <p style={{ fontSize: '0.85rem', color: MUTED }}>No bank accounts synced yet.</p>
          ) : (
            <div className="sd-stack" style={{ gap: '0.5rem' }}>
              {stats.bankAccounts.map((acct) => (
                <div key={acct.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '0.5rem', background: SURFACE_2, padding: '0.5rem 0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: TEXT }}>{acct.name}</div>
                    <div style={{ fontSize: '0.72rem', color: MUTED }}>{acct.currency}{acct.last_reconciled ? ` · Rec: ${acct.last_reconciled}` : ''}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: TEXT }}>{fmtMyr(acct.balance_myr)}</div>
                    {acct.currency !== 'MYR' && (
                      <div style={{ fontSize: '0.72rem', color: MUTED }}>{acct.currency} {acct.balance.toLocaleString()}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="sd-chart-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h3 className="sd-chart-title" style={{ marginBottom: 0 }}>Inflows vs Outflows vs Cumulative Cash</h3>
            <p className="sd-chart-sub">13-week rolling forecast</p>
          </div>
          <div className="sd-theme-seg" style={{ padding: '0.2rem' }}>
            {SCENARIOS.map((s) => (
              <button
                key={s}
                type="button"
                className={scenario === s ? 'active' : ''}
                onClick={() => setScenario(s)}
                style={{ fontSize: '0.72rem', padding: '0.3rem 0.6rem', borderRadius: '0.4rem' }}
              >
                {SCENARIO_LABEL[s]}
              </button>
            ))}
          </div>
        </div>
        <LineChart
          data={forecastData}
          xKey="week"
          yKey="cumulative"
          color={color}
          unit="RM "
          height={220}
          dataKeys={['inflow', 'outflow', 'cumulative']}
          colors={[color, 'var(--samurai-danger)', 'var(--samurai-lime)']}
          labels={{ inflow: 'Inflow', outflow: 'Outflow', cumulative: 'Cumulative Cash' }}
        />
      </div>

      {stats.fxPositions.length > 0 && (
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Treasury &amp; FX Exposure</h3>
          <p className="sd-chart-sub">BNM FEA compliance status by currency</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <th className="pb-2 text-left" style={{ fontSize: '0.72rem', fontWeight: 500, color: MUTED }}>Currency</th>
                  <th className="pb-2 text-right" style={{ fontSize: '0.72rem', fontWeight: 500, color: MUTED }}>Long</th>
                  <th className="pb-2 text-right" style={{ fontSize: '0.72rem', fontWeight: 500, color: MUTED }}>Short</th>
                  <th className="pb-2 text-right" style={{ fontSize: '0.72rem', fontWeight: 500, color: MUTED }}>Net Position</th>
                  <th className="pb-2 text-right" style={{ fontSize: '0.72rem', fontWeight: 500, color: MUTED }}>BNM FEA</th>
                </tr>
              </thead>
              <tbody>
                {stats.fxPositions.map((fx) => (
                  <tr key={fx.currency} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="py-2" style={{ fontWeight: 600, color: TEXT }}>{fx.currency}</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{fx.long.toLocaleString()}</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{fx.short.toLocaleString()}</td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: fx.net >= 0 ? 'var(--samurai-ok)' : 'var(--samurai-danger)' }}>
                      {fx.net >= 0 ? '+' : ''}{fx.net.toLocaleString()}
                    </td>
                    <td className="py-2 text-right">
                      <span className={`sd-chip ${fx.bnm_fea_compliant ? 'ok' : 'bad'}`}>{fx.bnm_fea_compliant ? 'Compliant' : 'Review'}</span>
                    </td>
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
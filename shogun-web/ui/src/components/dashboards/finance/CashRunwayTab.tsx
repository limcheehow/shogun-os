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

const FEA_BADGE = (ok: boolean) =>
  ok ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700';

export function CashRunwayTab({ stats, color }: Props) {
  const [scenario, setScenario] = useState<Scenario>('expected');
  const forecastData = stats.forecast13w[scenario] ?? [];
  const totalBurn = stats.fixedOpex + stats.variableOpex;
  const fixedPct = totalBurn > 0 ? (stats.fixedOpex / totalBurn) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Runway & Burn Breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-5">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Cash Runway</div>
          <div className="mt-1 text-4xl font-bold text-slate-900">
            {stats.cashRunwayMonths > 0 ? `${stats.cashRunwayMonths.toFixed(1)}` : '—'}
            <span className="ml-1 text-lg font-normal text-slate-500">months</span>
          </div>
          <div className={`mt-2 inline-block rounded-full px-3 py-1 text-xs font-semibold
            ${stats.runwayStatus === 'healthy' ? 'bg-emerald-100 text-emerald-700' :
              stats.runwayStatus === 'caution' ? 'bg-amber-100 text-amber-700' :
              stats.runwayStatus === 'critical' ? 'bg-rose-100 text-rose-700' :
              'bg-slate-100 text-slate-500'}`}>
            {stats.runwayStatus === 'healthy' ? '✓ Healthy (>6 months)' :
             stats.runwayStatus === 'caution' ? '⚠ Caution (3–6 months)' :
             stats.runwayStatus === 'critical' ? '⛔ Critical (<3 months)' : 'Unknown'}
          </div>
          <div className="mt-4">
            <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
              <span>Fixed OPEX (Payroll/Rent/Cloud)</span>
              <span className="font-semibold">{fmtMyr(stats.fixedOpex)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-emerald-500" style={{ width: `${fixedPct}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
              <span>Variable OPEX (Mktg/Travel/Other)</span>
              <span className="font-semibold">{fmtMyr(stats.variableOpex)}</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-amber-400" style={{ width: `${100 - fixedPct}%` }} />
            </div>
          </div>
        </div>

        {/* Bank Account Balances */}
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Bank Accounts</h3>
          {stats.bankAccounts.length === 0 ? (
            <p className="text-sm text-slate-400">No bank accounts synced yet.</p>
          ) : (
            <div className="space-y-2">
              {stats.bankAccounts.map((acct) => (
                <div key={acct.name} className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{acct.name}</div>
                    <div className="text-xs text-slate-500">{acct.currency}{acct.last_reconciled ? ` · Rec: ${acct.last_reconciled}` : ''}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-slate-900">{fmtMyr(acct.balance_myr)}</div>
                    {acct.currency !== 'MYR' && (
                      <div className="text-xs text-slate-400">{acct.currency} {acct.balance.toLocaleString()}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 13-Week Forecast */}
      <div className="card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Inflows vs Outflows vs Cumulative Cash (13-Wk Forecast)</h3>
          <div className="flex gap-1">
            {SCENARIOS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setScenario(s)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
                  scenario === s
                    ? 'bg-brand text-white shadow-sm'
                    : 'border border-surface-border bg-white text-slate-500 hover:border-slate-300'
                }`}
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
          colors={[color, '#f43f5e', '#6366f1']}
          labels={{ inflow: 'Inflow', outflow: 'Outflow', cumulative: 'Cumulative Cash' }}
        />
      </div>

      {/* FX Exposure */}
      {stats.fxPositions.length > 0 && (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Treasury & FX Exposure</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">Currency</th>
                  <th className="pb-2 text-right font-medium">Long</th>
                  <th className="pb-2 text-right font-medium">Short</th>
                  <th className="pb-2 text-right font-medium">Net Position</th>
                  <th className="pb-2 text-right font-medium">BNM FEA</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.fxPositions.map((fx) => (
                  <tr key={fx.currency}>
                    <td className="py-2 font-semibold text-slate-800">{fx.currency}</td>
                    <td className="py-2 text-right text-slate-700">{fx.long.toLocaleString()}</td>
                    <td className="py-2 text-right text-slate-700">{fx.short.toLocaleString()}</td>
                    <td className={`py-2 text-right font-semibold ${fx.net >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {fx.net >= 0 ? '+' : ''}{fx.net.toLocaleString()}
                    </td>
                    <td className="py-2 text-right">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${FEA_BADGE(fx.bnm_fea_compliant)}`}>
                        {fx.bnm_fea_compliant ? 'Compliant' : 'Review'}
                      </span>
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

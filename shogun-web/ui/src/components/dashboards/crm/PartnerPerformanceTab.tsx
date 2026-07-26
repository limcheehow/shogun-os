import { BarChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';
import { chartColors } from '../../../lib/palette';

interface Props { stats: CeoDashboardStats; color: string }

export function PartnerPerformanceTab({ stats, color }: Props) {
  const multiColors = chartColors(color, 3);

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Partner Booking Leaderboard</h3>
        <BarChart
          data={stats.byPartner}
          xKey="partner"
          yKey="booking"
          color={color}
          unit="RM "
          height={250}
        />
      </div>

      {stats.byManagerByPartner.length > 0 && (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Manager x Partner Matrix</h3>
          <BarChart
            data={stats.byManagerByPartner}
            xKey="partner"
            yKey="deals"
            color={color}
            colors={multiColors}
            height={200}
          />
        </div>
      )}

      {/* Partner at-risk alerts */}
      {stats.atRiskByPartner.length > 0 && (
        <div className="card overflow-hidden">
          <div className="border-b border-surface-border px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-700">At-Risk Partner Deals</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs font-medium uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2">Partner</th>
                  <th className="px-4 py-2">Primary Owner</th>
                  <th className="px-4 py-2 text-right">At-Risk Deals</th>
                  <th className="px-4 py-2 text-right">At-Risk Value</th>
                </tr>
              </thead>
              <tbody>
                {stats.atRiskByPartner.map((p) => (
                  <tr key={p.partner} className="border-b border-surface-border last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-2 font-medium text-slate-900">{p.partner}</td>
                    <td className="px-4 py-2 text-slate-600">{p.primaryOwner}</td>
                    <td className="px-4 py-2 text-right text-rose-600">{p.atRiskDeals}</td>
                    <td className="px-4 py-2 text-right text-rose-600">RM {(p.atRiskValue / 1000).toFixed(0)}K</td>
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
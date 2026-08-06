import { BarChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';
import { chartColors } from '../../../lib/palette';

interface Props { stats: CeoDashboardStats; color: string }

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;

function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function PartnerPerformanceTab({ stats, color }: Props) {
  const multiColors = chartColors(color, 3);

  return (
    <div className="sd-stack">
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Partner Booking Leaderboard</h3>
        <p className="sd-chart-sub">Total bookings attributed to each partner</p>
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
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Manager x Partner Matrix</h3>
          <p className="sd-chart-sub">Deal counts across managers and partners</p>
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
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">At-Risk Partner Deals</h3>
          <p className="sd-chart-sub">Stalled deals (&gt;30 days) grouped by partner</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Partner</Th>
                  <Th align="left">Primary Owner</Th>
                  <Th align="right">At-Risk Deals</Th>
                  <Th align="right">At-Risk Value</Th>
                </tr>
              </thead>
              <tbody>
                {stats.atRiskByPartner.map((p, i) => (
                  <tr key={p.partner} style={{ borderBottom: `1px solid ${BORDER}`, background: i % 2 === 1 ? SURFACE_2 : undefined }}>
                    <td className="px-3 py-2.5" style={{ fontWeight: 600, color: TEXT }}>{p.partner}</td>
                    <td className="px-3 py-2.5" style={{ color: MUTED }}>{p.primaryOwner}</td>
                    <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: 'var(--samurai-danger)' }}>{p.atRiskDeals}</td>
                    <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: 'var(--samurai-danger)' }}>RM {(p.atRiskValue / 1000).toFixed(0)}K</td>
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

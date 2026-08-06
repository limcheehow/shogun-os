import { AlertTriangle } from 'lucide-react';
import { BarChart } from '../charts';
import type { ProcurementDashboardStats } from '../../../lib/types';

interface Props { stats: ProcurementDashboardStats; color: string }

const MOVEMENT_BADGE: Record<string, string> = {
  '+ Receive':    'ok',
  '- Issue':      'muted',
  '~ Adjustment': 'warn',
  '! Damage':     'bad',
  '↺ Return':     'muted',
};

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const BORDER = 'var(--samurai-border)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function StockMovementAuditTab({ stats, color }: Props) {
  return (
    <div className="sd-stack">
      {/* Inventory Loss & Shrinkage Flag Banner */}
      {stats.shrinkageFlagItems.length > 0 && (
        <div className="sd-alert-row critical">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span className="flex-1">
            Shrinkage flag — {stats.shrinkageFlagItems.length} SKU{stats.shrinkageFlagItems.length > 1 ? 's' : ''} with damage/adjustment entries exceeding 2% of total stock: {stats.shrinkageFlagItems.join(', ')}
          </span>
        </div>
      )}

      {/* Stock Movement Timeline & Audit Table */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Stock Movement Audit Log (Immutable Timeline)</h3>
        {stats.stockMovements.length === 0 ? (
          <p style={{ color: MUTED, padding: '1rem 0' }}>No stock movements recorded yet. Chotatsu (Procurement Agent) appends entries on every receive/issue/adjustment.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Timestamp</Th>
                  <Th align="left">SKU & Item</Th>
                  <Th align="center">Type</Th>
                  <Th align="right">Quantity</Th>
                  <Th align="left">Reference ID</Th>
                  <Th align="left">Location</Th>
                  <Th align="left">Actor / Agent</Th>
                </tr>
              </thead>
              <tbody>
                {stats.stockMovements.map((m, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-3 py-2.5" style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', color: MUTED }}>{m.timestamp}</td>
                    <td className="px-3 py-2.5">
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', fontWeight: 600, color: TEXT }}>{m.sku}</div>
                      <div style={{ fontSize: '0.72rem', color: MUTED }}>{m.item_name}</div>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`sd-chip ${MOVEMENT_BADGE[m.movement_type] ?? 'muted'}`}>
                        {m.movement_type}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: m.movement_type.startsWith('+') || m.movement_type.startsWith('↺') ? 'var(--samurai-ok)' : m.movement_type.startsWith('!') ? 'var(--samurai-danger)' : TEXT }}>
                      {m.movement_type.startsWith('-') ? '-' : m.movement_type.startsWith('+') || m.movement_type.startsWith('↺') ? '+' : ''}{m.quantity.toLocaleString()}
                    </td>
                    <td className="px-3 py-2.5" style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', color: MUTED }}>{m.reference_id}</td>
                    <td className="px-3 py-2.5" style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', color: MUTED }}>{m.location_id}</td>
                    <td className="px-3 py-2.5" style={{ fontSize: '0.72rem', color: MUTED }}>{m.actor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Movement Type Distribution Chart */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Movement Type Distribution (Monthly)</h3>
        {stats.movementTypeDistribution.length === 0 ? (
          <p style={{ color: MUTED, padding: '1rem 0' }}>No movement distribution data available yet.</p>
        ) : (
          <BarChart
            data={stats.movementTypeDistribution}
            xKey="movement_type"
            yKey="quantity"
            color={color}
            unit=""
            height={220}
            dataKeys={['quantity']}
            colors={[color]}
          />
        )}
      </div>
    </div>
  );
}

import { AlertTriangle } from 'lucide-react';
import { BarChart } from '../charts';
import type { ProcurementDashboardStats } from '../../../lib/types';

interface Props { stats: ProcurementDashboardStats; color: string }

const MOVEMENT_BADGE: Record<string, string> = {
  '+ Receive':    'bg-emerald-100 text-emerald-700',
  '- Issue':      'bg-blue-100 text-blue-700',
  '~ Adjustment': 'bg-amber-100 text-amber-700',
  '! Damage':     'bg-rose-100 text-rose-700',
  '↺ Return':     'bg-indigo-100 text-indigo-700',
};

export function StockMovementAuditTab({ stats, color }: Props) {
  return (
    <div className="space-y-4">
      {/* Inventory Loss & Shrinkage Flag Banner */}
      {stats.shrinkageFlagItems.length > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            Shrinkage flag — {stats.shrinkageFlagItems.length} SKU{stats.shrinkageFlagItems.length > 1 ? 's' : ''} with damage/adjustment entries exceeding 2% of total stock: {stats.shrinkageFlagItems.join(', ')}
          </span>
        </div>
      )}

      {/* Stock Movement Timeline & Audit Table */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Stock Movement Audit Log (Immutable Timeline)</h3>
        {stats.stockMovements.length === 0 ? (
          <p className="text-sm text-slate-400">No stock movements recorded yet. Chotatsu (Procurement Agent) appends entries on every receive/issue/adjustment.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">Timestamp</th>
                  <th className="pb-2 text-left font-medium">SKU & Item</th>
                  <th className="pb-2 text-center font-medium">Type</th>
                  <th className="pb-2 text-right font-medium pr-8">Quantity</th>
                  <th className="pb-2 text-left font-medium pl-6">Reference ID</th>
                  <th className="pb-2 text-left font-medium">Location</th>
                  <th className="pb-2 text-left font-medium">Actor / Agent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.stockMovements.map((m, i) => (
                  <tr key={i} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-mono text-xs text-slate-600">{m.timestamp}</td>
                    <td className="py-2">
                      <div className="font-mono text-xs font-medium text-slate-800">{m.sku}</div>
                      <div className="text-xs text-slate-500">{m.item_name}</div>
                    </td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${MOVEMENT_BADGE[m.movement_type] ?? 'bg-slate-100 text-slate-600'}`}>
                        {m.movement_type}
                      </span>
                    </td>
                    <td className={`py-2 text-right font-semibold pr-8 ${m.movement_type.startsWith('+') || m.movement_type.startsWith('↺') ? 'text-emerald-600' : m.movement_type.startsWith('!') ? 'text-rose-600' : 'text-slate-800'}`}>
                      {m.movement_type.startsWith('-') ? '-' : m.movement_type.startsWith('+') || m.movement_type.startsWith('↺') ? '+' : ''}{m.quantity.toLocaleString()}
                    </td>
                    <td className="py-2 font-mono text-xs text-slate-600 pl-6">{m.reference_id}</td>
                    <td className="py-2 font-mono text-xs text-slate-600">{m.location_id}</td>
                    <td className="py-2 text-xs text-slate-600">{m.actor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Movement Type Distribution Chart */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Movement Type Distribution (Monthly)</h3>
        {stats.movementTypeDistribution.length === 0 ? (
          <p className="text-sm text-slate-400">No movement distribution data available yet.</p>
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

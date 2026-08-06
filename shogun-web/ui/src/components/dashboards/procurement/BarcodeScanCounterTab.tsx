import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Package, Warehouse, AlertTriangle, ArrowLeftRight } from 'lucide-react';
import { BarChart } from '../charts';
import type { BarcodeBatchLog, ProcurementDashboardStats } from '../../../lib/types';

interface Props {
  stats: ProcurementDashboardStats;
  color?: string;
}

const DEFAULT_BATCHES: BarcodeBatchLog[] = [
  {
    batch_id: 'BATCH-2026-0803-01',
    action_type: 'GRN Receipt Tagging',
    reference_id: 'GRN-2026-0091 (PO-2026-0218)',
    actor: 'Warehouse / Logistics',
    timestamp: '2026-08-03 10:15',
    total_items: 4,
    units: [
      { barcode_id: 'BC-984201-001', sku: 'IT-LP-15', item_name: 'Dell Latitude 5540 i7', serial_no: 'SN-5540-001', location_bin: 'LOC-MAIN-A1', status: 'In Store', last_scan_timestamp: '2026-08-03 10:15' },
      { barcode_id: 'BC-984201-002', sku: 'IT-LP-15', item_name: 'Dell Latitude 5540 i7', serial_no: 'SN-5540-002', location_bin: 'LOC-MAIN-A1', status: 'Issued', assigned_to: 'Admin Dept (REQ-2026-0845)', last_scan_timestamp: '2026-08-03 14:20' },
      { barcode_id: 'BC-984201-003', sku: 'IT-LP-15', item_name: 'Dell Latitude 5540 i7', serial_no: 'SN-5540-003', location_bin: 'LOC-MAIN-A1', status: 'In Store', last_scan_timestamp: '2026-08-03 10:15' },
      { barcode_id: 'BC-984201-004', sku: 'IT-LP-15', item_name: 'Dell Latitude 5540 i7', serial_no: 'SN-5540-004', location_bin: 'LOC-MAIN-A1', status: 'In Store', last_scan_timestamp: '2026-08-03 10:15' },
    ],
  },
  {
    batch_id: 'BATCH-2026-0802-04',
    action_type: 'Stock Issuance (Scan OUT)',
    reference_id: 'REQ-2026-0845',
    actor: 'IT Infrastructure',
    timestamp: '2026-08-02 14:40',
    total_items: 2,
    units: [
      { barcode_id: 'BC-884102-011', sku: 'OF-PR-03', item_name: 'A4 80gsm Ream', serial_no: 'BATCH-PAP-881', location_bin: 'LOC-OFF-B2', status: 'Issued', assigned_to: 'IT Dept Staff', last_scan_timestamp: '2026-08-02 14:40' },
      { barcode_id: 'BC-884102-012', sku: 'OF-PR-03', item_name: 'A4 80gsm Ream', serial_no: 'BATCH-PAP-882', location_bin: 'LOC-OFF-B2', status: 'Issued', assigned_to: 'IT Dept Staff', last_scan_timestamp: '2026-08-02 14:40' },
    ],
  },
  {
    batch_id: 'BATCH-2026-0801-02',
    action_type: 'Stock Return (Scan IN)',
    reference_id: 'RTV-2026-0008',
    actor: 'Store & Facilities',
    timestamp: '2026-08-01 11:20',
    total_items: 1,
    units: [
      { barcode_id: 'BC-984201-088', sku: 'IT-LP-15', item_name: 'Dell Latitude 5540 i7', serial_no: 'SN-5540-088', location_bin: 'LOC-MAIN-A1', status: 'Returned', assigned_to: 'RMA Store Return', last_scan_timestamp: '2026-08-01 11:20' },
    ],
  },
];

const MOVEMENT_BADGE: Record<string, string> = {
  '+ Receive':    'bg-emerald-100 text-emerald-700',
  '- Issue':      'bg-blue-100 text-blue-700',
  '~ Adjustment': 'bg-amber-100 text-amber-700',
  '! Damage':     'bg-rose-100 text-rose-700',
  '↺ Return':     'bg-indigo-100 text-indigo-700',
};

export function BarcodeScanCounterTab({ stats, color = '#2563eb' }: Props) {
  // Batch Logs State
  const batches = stats.barcodeBatches && stats.barcodeBatches.length > 0 ? stats.barcodeBatches : DEFAULT_BATCHES;
  const [expandedBatchIds, setExpandedBatchIds] = useState<Record<string, boolean>>({
    'BATCH-2026-0803-01': true, // default expand 1st batch
  });

  const toggleExpand = (batchId: string) => {
    setExpandedBatchIds((prev) => ({ ...prev, [batchId]: !prev[batchId] }));
  };

  return (
    <div className="space-y-4">
      {/* Inventory Loss & Shrinkage Flag Banner */}
      {stats.shrinkageFlagItems && stats.shrinkageFlagItems.length > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            Shrinkage flag — {stats.shrinkageFlagItems.length} SKU{stats.shrinkageFlagItems.length > 1 ? 's' : ''} with damage/adjustment entries exceeding 2% of total stock: {stats.shrinkageFlagItems.join(', ')}
          </span>
        </div>
      )}

      {/* Warehouse Bin Capacity & Location Utilisation */}
      <div className="card p-4">
        <div className="mb-3 flex items-center gap-2">
          <Warehouse className="h-4 w-4 text-brand" />
          <h3 className="text-sm font-semibold text-slate-800">Warehouse Bin Capacity & Location Utilisation</h3>
        </div>
        {stats.warehouseBinCapacity.length === 0 ? (
          <p className="text-sm text-slate-400">No warehouse bin data available yet.</p>
        ) : (
          <div className="space-y-3">
            {stats.warehouseBinCapacity.map((bin) => {
              const over = bin.utilisation_pct > 85;
              return (
                <div key={bin.location}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-700">{bin.location}</span>
                    <span className="text-slate-500">
                      {bin.used.toLocaleString()} / {bin.capacity.toLocaleString()} units · {bin.utilisation_pct.toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-2 rounded-full transition-all ${over ? 'bg-rose-500' : bin.utilisation_pct > 70 ? 'bg-amber-400' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(bin.utilisation_pct, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Inventory Batch Barcode Scan Logs Table */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <h4 className="text-sm font-semibold text-slate-800">Inventory Batch Barcode Scan Logs</h4>
          <span className="text-xs text-slate-400">Click any batch row to expand individual stock items</span>
        </div>

        <div className="overflow-x-auto rounded-lg border border-surface-border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-slate-50/80 text-xs font-semibold text-slate-500">
                <th className="w-10 px-3 py-2.5 text-center"></th>
                <th className="px-3 py-2.5 text-left font-medium">Batch ID</th>
                <th className="px-3 py-2.5 text-left font-medium">Action Type</th>
                <th className="px-3 py-2.5 text-left font-medium">Reference ID</th>
                <th className="px-3 py-2.5 text-center font-medium">Items Count</th>
                <th className="px-3 py-2.5 text-left font-medium">Department</th>
                <th className="px-3 py-2.5 text-left font-medium">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {batches.map((batch) => {
                const isExpanded = !!expandedBatchIds[batch.batch_id];
                return (
                  <React.Fragment key={batch.batch_id}>
                    {/* Master Batch Row */}
                    <tr
                      onClick={() => toggleExpand(batch.batch_id)}
                      className="cursor-pointer hover:bg-slate-50 transition-colors font-medium text-slate-800"
                    >
                      <td className="w-10 px-3 py-2.5 text-center text-slate-400">
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </td>
                      <td className="px-3 py-2.5 text-left font-mono text-xs font-bold text-slate-900">{batch.batch_id}</td>
                      <td className="px-3 py-2.5 text-left">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${batch.action_type.includes('GRN') ? 'bg-blue-100 text-blue-800' : batch.action_type.includes('OUT') ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'}`}>
                          {batch.action_type}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-left font-mono text-xs text-slate-600">{batch.reference_id}</td>
                      <td className="px-3 py-2.5 text-center font-bold text-slate-900">{batch.total_items} units</td>
                      <td className="px-3 py-2.5 text-left text-slate-600">{batch.actor}</td>
                      <td className="px-3 py-2.5 text-left font-mono text-xs text-slate-500">{batch.timestamp}</td>
                    </tr>

                    {/* Expanded Detail Accordion Sub-Table */}
                    {isExpanded && (
                      <tr className="bg-slate-50/80">
                        <td colSpan={7} className="p-3 pl-10">
                          <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
                            <div className="text-xs font-bold text-slate-700 flex items-center gap-1.5 border-b border-slate-100 pb-1.5">
                              <Package className="h-3.5 w-3.5 text-brand" /> Stock Items in {batch.batch_id}:
                            </div>
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="text-slate-400 text-left border-b border-slate-100 pb-1 font-semibold">
                                  <th className="py-1">Barcode ID</th>
                                  <th className="py-1">SKU & Item Name</th>
                                  <th className="py-1">Serial Number</th>
                                  <th className="py-1">Location Bin</th>
                                  <th className="py-1">Assigned / Status</th>
                                  <th className="py-1">Last Scan</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {batch.units.map((unit) => (
                                  <tr key={unit.barcode_id} className="hover:bg-slate-50/50">
                                    <td className="py-1.5 font-mono font-bold text-indigo-700">{unit.barcode_id}</td>
                                    <td className="py-1.5 font-medium text-slate-800">{unit.sku} — {unit.item_name}</td>
                                    <td className="py-1.5 font-mono text-slate-600">{unit.serial_no}</td>
                                    <td className="py-1.5 font-mono text-slate-600">{unit.location_bin}</td>
                                    <td className="py-1.5">
                                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${unit.status === 'In Store' ? 'bg-emerald-100 text-emerald-800' : unit.status === 'Issued' ? 'bg-amber-100 text-amber-800' : 'bg-indigo-100 text-indigo-800'}`}>
                                        {unit.status} {unit.assigned_to ? `(${unit.assigned_to})` : ''}
                                      </span>
                                    </td>
                                    <td className="py-1.5 font-mono text-slate-400">{unit.last_scan_timestamp}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Stock Movement Audit Log (Immutable Timeline) */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-surface-border pb-2">
          <ArrowLeftRight className="h-4 w-4 text-brand" />
          <h3 className="text-sm font-semibold text-slate-800">Stock Movement Audit Log (Immutable Timeline)</h3>
        </div>
        {stats.stockMovements.length === 0 ? (
          <p className="text-sm text-slate-400">No stock movements recorded yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-surface-border bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-slate-50/80 text-xs font-semibold text-slate-500">
                  <th className="px-3 py-2.5 text-left font-medium">Timestamp</th>
                  <th className="px-3 py-2.5 text-left font-medium">SKU & Item</th>
                  <th className="px-3 py-2.5 text-center font-medium">Type</th>
                  <th className="px-3 py-2.5 text-right font-medium pr-8">Quantity</th>
                  <th className="px-3 py-2.5 text-left font-medium pl-6">Reference ID</th>
                  <th className="px-3 py-2.5 text-left font-medium">Location</th>
                  <th className="px-3 py-2.5 text-left font-medium">Actor / Department</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.stockMovements.map((m, i) => (
                  <tr key={i} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-3 py-2.5 font-mono text-xs text-slate-600">{m.timestamp}</td>
                    <td className="px-3 py-2.5">
                      <div className="font-mono text-xs font-medium text-slate-800">{m.sku}</div>
                      <div className="text-xs text-slate-500">{m.item_name}</div>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${MOVEMENT_BADGE[m.movement_type] ?? 'bg-slate-100 text-slate-600'}`}>
                        {m.movement_type}
                      </span>
                    </td>
                    <td className={`px-3 py-2.5 text-right font-semibold pr-8 ${m.movement_type.startsWith('+') || m.movement_type.startsWith('↺') ? 'text-emerald-600' : m.movement_type.startsWith('!') ? 'text-rose-600' : 'text-slate-800'}`}>
                      {m.movement_type.startsWith('-') ? '-' : m.movement_type.startsWith('+') || m.movement_type.startsWith('↺') ? '+' : ''}{m.quantity.toLocaleString()}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-xs text-slate-600 pl-6">{m.reference_id}</td>
                    <td className="px-3 py-2.5 font-mono text-xs text-slate-600">{m.location_id}</td>
                    <td className="px-3 py-2.5 text-xs text-slate-600">{m.actor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Movement Type Distribution Chart */}
      {stats.movementTypeDistribution && stats.movementTypeDistribution.length > 0 && (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Movement Type Distribution (Monthly)</h3>
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
        </div>
      )}
    </div>
  );
}

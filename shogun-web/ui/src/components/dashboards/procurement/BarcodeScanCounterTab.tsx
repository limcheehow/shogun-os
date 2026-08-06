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
  '+ Receive':    'ok',
  '- Issue':      'muted',
  '~ Adjustment': 'warn',
  '! Damage':     'bad',
  '↺ Return':    'muted',
};

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const BORDER = 'var(--samurai-border)';
const SURFACE_2 = 'var(--samurai-surface-2)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

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
    <div className="sd-stack">
      {/* Inventory Loss & Shrinkage Flag Banner */}
      {stats.shrinkageFlagItems && stats.shrinkageFlagItems.length > 0 && (
        <div className="sd-alert-row critical">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            Shrinkage flag — {stats.shrinkageFlagItems.length} SKU{stats.shrinkageFlagItems.length > 1 ? 's' : ''} with damage/adjustment entries exceeding 2% of total stock: {stats.shrinkageFlagItems.join(', ')}
          </span>
        </div>
      )}

      {/* Warehouse Bin Capacity & Location Utilisation */}
      <div className="sd-chart-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <Warehouse className="h-4 w-4" style={{ color: 'var(--samurai-lime)' }} />
          <h3 className="sd-chart-title" style={{ margin: 0 }}>Warehouse Bin Capacity & Location Utilisation</h3>
        </div>
        {stats.warehouseBinCapacity.length === 0 ? (
          <p style={{ color: MUTED, fontSize: '0.85rem' }}>No warehouse bin data available yet.</p>
        ) : (
          <div className="sd-stack" style={{ gap: '0.75rem' }}>
            {stats.warehouseBinCapacity.map((bin) => {
              const over = bin.utilisation_pct > 85;
              return (
                <div key={bin.location}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.72rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 500, color: TEXT }}>{bin.location}</span>
                    <span style={{ color: MUTED }}>
                      {bin.used.toLocaleString()} / {bin.capacity.toLocaleString()} units · {bin.utilisation_pct.toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ height: '0.5rem', borderRadius: 999, overflow: 'hidden', background: SURFACE_2 }}>
                    <div
                      style={{ height: '100%', borderRadius: 999, background: over ? 'var(--samurai-danger)' : bin.utilisation_pct > 70 ? 'var(--samurai-warning)' : 'var(--samurai-ok)', width: `${Math.min(bin.utilisation_pct, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Inventory Batch Barcode Scan Logs Table */}
      <div className="sd-chart-card sd-stack" style={{ gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.5rem' }}>
          <h4 className="sd-chart-title" style={{ margin: 0 }}>Inventory Batch Barcode Scan Logs</h4>
          <span style={{ fontSize: '0.72rem', color: MUTED }}>Click any batch row to expand individual stock items</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                <th style={{ width: '2.5rem' }}></th>
                <Th align="left">Batch ID</Th>
                <Th align="left">Action Type</Th>
                <Th align="left">Reference ID</Th>
                <Th align="center">Items Count</Th>
                <Th align="left">Department</Th>
                <Th align="left">Timestamp</Th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => {
                const isExpanded = !!expandedBatchIds[batch.batch_id];
                return (
                  <React.Fragment key={batch.batch_id}>
                    {/* Master Batch Row */}
                    <tr
                      onClick={() => toggleExpand(batch.batch_id)}
                      style={{ borderBottom: `1px solid ${BORDER}`, cursor: 'pointer' }}
                    >
                      <td className="px-3 py-2.5 text-center" style={{ color: MUTED }}>
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </td>
                      <td className="px-3 py-2.5" style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', fontWeight: 700, color: TEXT }}>{batch.batch_id}</td>
                      <td className="px-3 py-2.5">
                        <span className={`sd-chip ${batch.action_type.includes('GRN') ? 'muted' : batch.action_type.includes('OUT') ? 'bad' : 'ok'}`}>
                          {batch.action_type}
                        </span>
                      </td>
                      <td className="px-3 py-2.5" style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', color: MUTED }}>{batch.reference_id}</td>
                      <td className="px-3 py-2.5 text-center" style={{ fontWeight: 700, color: TEXT }}>{batch.total_items} units</td>
                      <td className="px-3 py-2.5" style={{ color: MUTED }}>{batch.actor}</td>
                      <td className="px-3 py-2.5" style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', color: MUTED }}>{batch.timestamp}</td>
                    </tr>

                    {/* Expanded Detail Accordion Sub-Table */}
                    {isExpanded && (
                      <tr style={{ background: 'color-mix(in srgb, var(--samurai-surface-2) 70%, transparent)' }}>
                        <td colSpan={7} className="p-3.5 pl-8">
                          <div
                            style={{
                              borderRadius: '0.6rem',
                              borderLeft: '4px solid var(--samurai-lime)',
                              borderTop: `1px solid ${BORDER}`,
                              borderRight: `1px solid ${BORDER}`,
                              borderBottom: `1px solid ${BORDER}`,
                              background: 'color-mix(in srgb, var(--samurai-surface) 92%, var(--samurai-lime) 4%)',
                              boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.2), 0 2px 8px rgba(0,0,0,0.15)',
                              padding: '0.85rem 1rem',
                            }}
                          >
                            <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--samurai-lime)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.5rem', marginBottom: '0.65rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                <Package className="h-4 w-4" style={{ color: 'var(--samurai-lime)' }} />
                                <span>Batch Contents: {batch.batch_id}</span>
                                <span className="sd-chip ok" style={{ fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}>
                                  {batch.units.length} Barcode Unit{batch.units.length > 1 ? 's' : ''} Scanned
                                </span>
                              </div>
                              <span style={{ fontSize: '0.7rem', color: MUTED, fontFamily: 'var(--font-display)' }}>
                                Ref: {batch.reference_id}
                              </span>
                            </div>
                            <div style={{ overflowX: 'auto' }}>
                              <table className="w-full" style={{ fontSize: '0.72rem', borderCollapse: 'collapse' }}>
                                <thead>
                                  <tr style={{ borderBottom: `1px solid ${BORDER}`, background: 'color-mix(in srgb, var(--samurai-surface-2) 40%, transparent)' }}>
                                    <th className="py-1.5 px-2 text-left" style={{ ...th, color: 'var(--samurai-text)' }}>Barcode ID</th>
                                    <th className="py-1.5 px-2 text-left" style={{ ...th, color: 'var(--samurai-text)' }}>SKU & Item Name</th>
                                    <th className="py-1.5 px-2 text-left" style={{ ...th, color: 'var(--samurai-text)' }}>Serial Number</th>
                                    <th className="py-1.5 px-2 text-left" style={{ ...th, color: 'var(--samurai-text)' }}>Location Bin</th>
                                    <th className="py-1.5 px-2 text-left" style={{ ...th, color: 'var(--samurai-text)' }}>Assigned / Status</th>
                                    <th className="py-1.5 px-2 text-left" style={{ ...th, color: 'var(--samurai-text)' }}>Last Scan</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {batch.units.map((unit) => (
                                    <tr key={unit.barcode_id} style={{ borderBottom: `1px dashed ${BORDER}` }}>
                                      <td className="py-2 px-2" style={{ fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--samurai-lime)' }}>{unit.barcode_id}</td>
                                      <td className="py-2 px-2" style={{ fontWeight: 600, color: TEXT }}>{unit.sku} — {unit.item_name}</td>
                                      <td className="py-2 px-2" style={{ fontFamily: 'var(--font-display)', color: MUTED }}>{unit.serial_no}</td>
                                      <td className="py-2 px-2" style={{ fontFamily: 'var(--font-display)', color: TEXT, fontWeight: 500 }}>{unit.location_bin}</td>
                                      <td className="py-2 px-2">
                                        <span className={`sd-chip ${unit.status === 'In Store' ? 'ok' : unit.status === 'Issued' ? 'warn' : 'muted'}`}>
                                          {unit.status} {unit.assigned_to ? `(${unit.assigned_to})` : ''}
                                        </span>
                                      </td>
                                      <td className="py-2 px-2" style={{ fontFamily: 'var(--font-display)', color: MUTED }}>{unit.last_scan_timestamp}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
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
      <div className="sd-chart-card sd-stack" style={{ gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.5rem' }}>
          <ArrowLeftRight className="h-4 w-4" style={{ color: 'var(--samurai-lime)' }} />
          <h3 className="sd-chart-title" style={{ margin: 0 }}>Stock Movement Audit Log (Immutable Timeline)</h3>
        </div>
        {stats.stockMovements.length === 0 ? (
          <p style={{ color: MUTED, fontSize: '0.85rem' }}>No stock movements recorded yet.</p>
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
                  <Th align="left">Actor / Department</Th>
                </tr>
              </thead>
              <tbody>
                {stats.stockMovements.map((m, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-3 py-2.5" style={{ fontFamily: 'var(--font-display)', fontSize: '0.72rem', color: MUTED }}>{m.timestamp}</td>
                    <td className="px-3 py-2.5">
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', fontWeight: 600, color: TEXT }}>{m.sku}</div>
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
      {stats.movementTypeDistribution && stats.movementTypeDistribution.length > 0 && (
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Movement Type Distribution (Monthly)</h3>
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

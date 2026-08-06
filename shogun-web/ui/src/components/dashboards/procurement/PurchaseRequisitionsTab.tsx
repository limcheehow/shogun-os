import { useState } from 'react';
import type { ProcurementDashboardStats, PurchaseRequisition } from '../../../lib/types';

interface Props {
  stats: ProcurementDashboardStats;
  onAction?: (actionType: string, entity: any) => void;
}

const DEFAULT_PRS: PurchaseRequisition[] = [
  {
    pr_number: 'PR-2026-0042',
    requester: 'Johnathan Tan',
    department: 'Engineering / Operations',
    item_description: 'Dell Latitude 5540 Laptops (x 10 units)',
    category: 'IT Hardware',
    estimated_amount: 48000.0,
    priority: 'High',
    status: 'Pending Approval',
    created_at: '2026-08-04 09:30',
    justification: 'Replacement for onboarding new engineering cohort.',
  },
  {
    pr_number: 'PR-2026-0041',
    requester: 'Siti Sarah',
    department: 'Administration / Facilities',
    item_description: 'Ergonomic Mesh Chairs Elite (x 15 units)',
    category: 'Furniture',
    estimated_amount: 13350.0,
    priority: 'Medium',
    status: 'Approved',
    created_at: '2026-08-03 14:15',
    justification: 'Office expansion to 4th floor workstation area.',
  },
  {
    pr_number: 'PR-2026-0040',
    requester: 'Kevin Wong',
    department: 'Warehouse / Logistics',
    item_description: 'Industrial Barcode Label Printer & Adhesive Stock',
    category: 'Hardware & Tools',
    estimated_amount: 6800.0,
    priority: 'Urgent',
    status: 'Converted to RFQ/PO',
    created_at: '2026-08-02 11:00',
    justification: 'Required for Code 128 inventory tagging roll-out.',
  },
  {
    pr_number: 'PR-2026-0039',
    requester: 'Ahmad Faiz',
    department: 'IT Infrastructure',
    item_description: 'UPS Battery 12V 7Ah (x 50 units)',
    category: 'Spare Parts',
    estimated_amount: 4750.0,
    priority: 'Low',
    status: 'Approved',
    created_at: '2026-08-01 16:45',
    justification: 'Preventative maintenance for main server room UPS units.',
  },
];

const PRIORITY_STYLE: Record<string, string> = {
  Low: 'bg-slate-100 text-slate-600',
  Medium: 'bg-blue-100 text-blue-700',
  High: 'bg-amber-100 text-amber-700',
  Urgent: 'bg-rose-100 text-rose-700 font-bold',
};

const STATUS_STYLE: Record<string, string> = {
  Draft: 'bg-slate-100 text-slate-600',
  'Pending Approval': 'bg-amber-100 text-amber-800',
  Approved: 'bg-emerald-100 text-emerald-800',
  'Converted to RFQ/PO': 'bg-indigo-100 text-indigo-800',
  Rejected: 'bg-rose-100 text-rose-800',
};

export function PurchaseRequisitionsTab({ stats, onAction }: Props) {
  const prList = stats.purchaseRequisitions && stats.purchaseRequisitions.length > 0 ? stats.purchaseRequisitions : DEFAULT_PRS;
  const [filter, setFilter] = useState<'All' | 'Pending Approval' | 'Approved' | 'Converted to RFQ/PO'>('All');

  const filteredPrs = prList.filter((pr) => (filter === 'All' ? true : pr.status === filter));

  return (
    <div className="space-y-4">
      {/* Normal Header Card */}
      <div className="card p-4">
        <h3 className="text-base font-semibold text-slate-800">Purchase Requisitions (PR)</h3>
        <p className="text-xs text-slate-500">
          Requisition status log tracking internal demand from request through approval to RFQ conversion.
        </p>

        {/* Status Filter Pills */}
        <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
          <button
            type="button"
            onClick={() => setFilter('All')}
            className={`rounded-md px-3 py-1 font-medium transition-colors ${filter === 'All' ? 'bg-slate-800 text-white font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            All ({prList.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('Pending Approval')}
            className={`rounded-md px-3 py-1 font-medium transition-colors ${filter === 'Pending Approval' ? 'bg-amber-100 text-amber-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            Pending Approval ({prList.filter((p) => p.status === 'Pending Approval').length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('Approved')}
            className={`rounded-md px-3 py-1 font-medium transition-colors ${filter === 'Approved' ? 'bg-emerald-100 text-emerald-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            Approved ({prList.filter((p) => p.status === 'Approved').length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('Converted to RFQ/PO')}
            className={`rounded-md px-3 py-1 font-medium transition-colors ${filter === 'Converted to RFQ/PO' ? 'bg-indigo-100 text-indigo-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            Converted to RFQ/PO ({prList.filter((p) => p.status === 'Converted to RFQ/PO').length})
          </button>
        </div>
      </div>

      {/* PR List Table */}
      <div className="card p-4">
        {filteredPrs.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-400">No purchase requisitions matching filter "{filter}".</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-surface-border bg-white shadow-sm">
            <table className="w-full min-w-[850px] text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-slate-50/80 text-xs font-semibold text-slate-500">
                  <th className="px-3 py-2.5 text-left font-medium">PR ID</th>
                  <th className="px-3 py-2.5 text-left font-medium">Requester & Dept</th>
                  <th className="px-3 py-2.5 text-left font-medium">Item Description</th>
                  <th className="px-3 py-2.5 text-right font-medium">Est. Total</th>
                  <th className="px-3 py-2.5 text-center font-medium">Priority</th>
                  <th className="px-3 py-2.5 text-center font-medium">Status</th>
                  <th className="px-3 py-2.5 text-center font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filteredPrs.map((pr) => (
                  <tr key={pr.pr_number} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-3 py-2.5 font-mono text-xs font-semibold text-slate-800">{pr.pr_number}</td>
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-slate-800">{pr.requester}</div>
                      <div className="text-xs text-slate-500">{pr.department}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-slate-800">{pr.item_description}</div>
                      {pr.justification && <div className="text-xs text-slate-400 italic">"{pr.justification}"</div>}
                    </td>
                    <td className="px-3 py-2.5 text-right font-semibold text-slate-900">RM {pr.estimated_amount.toLocaleString()}</td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${PRIORITY_STYLE[pr.priority]}`}>
                        {pr.priority}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLE[pr.status]}`}>
                        {pr.status}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <div className="flex justify-center gap-1.5">
                        {pr.status === 'Pending Approval' && (
                          <>
                            <button
                              type="button"
                              onClick={() => onAction?.('approve_pr', pr)}
                              className="rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700 transition-colors"
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              onClick={() => onAction?.('reject_pr', pr)}
                              className="rounded-md bg-rose-100 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-200 transition-colors"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {pr.status === 'Approved' && (
                          <button
                            type="button"
                            onClick={() => onAction?.('convert_to_rfq', pr)}
                            className="rounded-md bg-brand px-2.5 py-1 text-xs font-medium text-white hover:opacity-90 transition-opacity"
                          >
                            Send to RFQ
                          </button>
                        )}
                        {pr.status === 'Converted to RFQ/PO' && (
                          <span className="text-xs text-slate-400 italic">Converted</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

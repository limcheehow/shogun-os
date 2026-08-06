import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { PieChart } from '../charts';
import { chartColors } from '../../../lib/palette';
import type { ExecutiveApprovalRow, ProcurementDashboardStats, PurchaseOrderRow } from '../../../lib/types';

interface Props {
  stats: ProcurementDashboardStats;
  color: string;
  onAction?: (actionType: string, entity: unknown) => void;
}

const fmtMyr = (n: number) =>
  n >= 1_000_000 ? `RM ${(n / 1_000_000).toFixed(2)}M` : `RM ${(n / 1_000).toFixed(0)}K`;

const FULFILLMENT_STYLE: Record<string, string> = {
  'Draft':               'bg-slate-100 text-slate-600',
  'Pending Approval':    'bg-amber-100 text-amber-700',
  'Issued to Vendor':    'bg-blue-100 text-blue-700',
  'Partially Received':  'bg-indigo-100 text-indigo-700',
  'Fully Received & Billed': 'bg-emerald-100 text-emerald-700',
};

const APPROVAL_STYLE: Record<string, string> = {
  'Draft':            'bg-slate-100 text-slate-600',
  'Pending Approval': 'bg-amber-100 text-amber-700',
  'Approved':         'bg-emerald-100 text-emerald-700',
  'Issued':           'bg-blue-100 text-blue-700',
  'Cancelled':        'bg-rose-100 text-rose-700',
};

const SLA_STYLE: Record<string, string> = {
  'Top Tier':     'bg-emerald-100 text-emerald-700',
  'Satisfactory': 'bg-blue-100 text-blue-700',
  'Under Review': 'bg-amber-100 text-amber-700',
};

const APPROVAL_QUEUE_STYLE: Record<string, string> = {
  'Pending Executive Approval': 'bg-amber-100 text-amber-700',
  'Approved':                    'bg-emerald-100 text-emerald-700',
  'Clarification Requested':    'bg-purple-100 text-purple-700',
  'Rejected':                   'bg-rose-100 text-rose-700',
};

export function PurchaseOrdersVendorTab({ stats, color, onAction }: Props) {
  const [statusFilter, setStatusFilter] = useState<string>('Pending Executive Approval');
  const [activePoApprovalFilter, setActivePoApprovalFilter] = useState<string>('All');
  const [poActionTarget, setPoActionTarget] = useState<PurchaseOrderRow | null>(null);
  const [execActionTarget, setExecActionTarget] = useState<ExecutiveApprovalRow | null>(null);

  const approvalQueue = stats.executiveApprovalQueue ?? [];
  const filteredQueue = approvalQueue.filter((item) => {
    if (statusFilter === 'All') return true;
    return item.approval_status === statusFilter;
  });

  const countPending = approvalQueue.filter((i) => i.approval_status === 'Pending Executive Approval').length;
  const countClarification = approvalQueue.filter((i) => i.approval_status === 'Clarification Requested').length;

  const activePos = stats.activePurchaseOrders ?? [];
  const filteredActivePos = activePos.filter((po) => {
    if (activePoApprovalFilter === 'All') return true;
    return po.approval_status === activePoApprovalFilter;
  });

  const countActiveAll = activePos.length;
  const countActiveApproved = activePos.filter((p) => p.approval_status === 'Approved').length;
  const countActiveIssued = activePos.filter((p) => p.approval_status === 'Issued').length;
  const countActivePending = activePos.filter((p) => p.approval_status === 'Pending Approval').length;
  const countActiveCancelled = activePos.filter((p) => p.approval_status === 'Cancelled').length;

  const concentrationAlert = stats.vendorSpendConcentration.find((v) => v.spend_pct > 25);

  return (
    <div className="space-y-4">
      {/* PO Pipeline Card (Restored Previous Design) */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">PO Lifecycle Pipeline (Funnel)</h3>
        {stats.poPipeline.length === 0 ? (
          <p className="text-sm text-slate-400">No PO pipeline stages available yet.</p>
        ) : (
          <>
            <div className="mb-2 flex h-8 overflow-hidden rounded-lg bg-surface-muted">
              {stats.poPipeline.map((stage, i) => {
                const totalCount = stats.poPipeline.reduce((sum, s) => sum + s.count, 0);
                const widthPct = totalCount > 0 ? (stage.count / totalCount) * 100 : 0;
                const colors = ['bg-slate-500', 'bg-amber-500', 'bg-blue-500', 'bg-indigo-500', 'bg-emerald-500'];
                return (
                  <div
                    key={stage.stage}
                    className={`flex items-center justify-center text-xs font-semibold text-white transition-all ${colors[i % colors.length]}`}
                    style={{ width: `${widthPct}%` }}
                    title={`${stage.stage}: ${stage.count} POs (${fmtMyr(stage.value)})`}
                  >
                    {widthPct > 8 && <span>{stage.count}</span>}
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between gap-2 overflow-x-auto pb-1 text-xs text-slate-500">
              {stats.poPipeline.map((stage) => (
                <div key={stage.stage} className="shrink-0 text-center">
                  <div className="font-semibold text-slate-800">{stage.stage}</div>
                  <div className="text-slate-500">{stage.count} POs · {fmtMyr(stage.value)}</div>
                </div>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Pipeline flow: Draft → Pending Approval → Issued to Vendor → Partially Received → Fully Received & Billed
            </p>
          </>
        )}
      </div>

      {/* Executive PO Approval Queue (> MYR 10,000) */}
      <div className="card p-4">
        <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-700">Executive PO Approval Queue (&gt; MYR 10,000)</h3>
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">CEO / CFO / CPO sign-off</span>
          </div>
          <div className="flex gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => setStatusFilter('Pending Executive Approval')}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${statusFilter === 'Pending Executive Approval' ? 'bg-amber-100 text-amber-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              Pending Approval ({countPending})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter('Clarification Requested')}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${statusFilter === 'Clarification Requested' ? 'bg-purple-100 text-purple-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              Clarification Requested ({countClarification})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter('All')}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${statusFilter === 'All' ? 'bg-slate-800 text-white font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              All ({approvalQueue.length})
            </button>
          </div>
        </div>
        <p className="mb-3 text-xs text-slate-400">
          Requisitions above the MYR 10,000 executive approval threshold. Requires sign-off before vendor issue.
        </p>
        {filteredQueue.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-400">No POs matching status "{statusFilter}".</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-surface-border bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-slate-50/80 text-xs font-semibold text-slate-500">
                  <th className="px-3 py-2.5 text-left font-medium">PO Number</th>
                  <th className="px-3 py-2.5 text-left font-medium">Vendor</th>
                  <th className="px-3 py-2.5 text-left font-medium">Order Date</th>
                  <th className="px-3 py-2.5 pr-8 text-right font-medium">Total Amount</th>
                  <th className="px-3 py-2.5 pl-6 text-left font-medium">Requester / Dept</th>
                  <th className="px-3 py-2.5 text-right font-medium">Threshold</th>
                  <th className="px-3 py-2.5 text-center font-medium">Status</th>
                  <th className="px-3 py-2.5 text-center font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filteredQueue.map((po) => (
                  <tr key={po.po_number} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-3 py-2.5 font-mono text-xs font-medium text-slate-800">{po.po_number}</td>
                    <td className="px-3 py-2.5 font-medium text-slate-800">{po.vendor}</td>
                    <td className="px-3 py-2.5 text-slate-600">{po.order_date}</td>
                    <td className="px-3 py-2.5 pr-8 text-right font-semibold text-slate-900">RM {po.total_amount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                    <td className="px-3 py-2.5 pl-6 text-slate-600">{po.requester_dept}</td>
                    <td className="px-3 py-2.5 text-right text-slate-600">RM {po.threshold_myr.toLocaleString()}</td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${APPROVAL_QUEUE_STYLE[po.approval_status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {po.approval_status}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <button
                        type="button"
                        onClick={() => setExecActionTarget(po)}
                        className="rounded-md bg-brand px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:opacity-90 transition-opacity"
                      >
                        Action
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Executive PO Approval Action Modal Dialog */}
      {execActionTarget && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default bg-black/30" onClick={() => setExecActionTarget(null)} aria-label="Close" />
          <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16" onClick={() => setExecActionTarget(null)}>
            <div className="card relative z-50 w-full max-w-md overflow-hidden bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Executive PO Approval Action</h2>
                  <p className="text-xs text-slate-500">{execActionTarget.vendor} · {execActionTarget.po_number}</p>
                </div>
                <button type="button" onClick={() => setExecActionTarget(null)} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 px-5 py-4 bg-slate-50/50">
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">PO Total Amount</div>
                  <div className="text-base font-bold text-slate-900">RM {execActionTarget.total_amount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">Requester Dept</div>
                  <div className="text-base font-bold text-brand">{execActionTarget.requester_dept}</div>
                </div>
              </div>

              <div className="border-t border-surface-border px-5 py-4">
                <p className="mb-3 text-xs text-slate-500 font-medium">Select action to send to Chotatsu (Procurement Agent):</p>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('approve_po', execActionTarget);
                      setExecActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-emerald-300 bg-emerald-50/60 px-4 py-2.5 text-left text-sm font-semibold text-emerald-900 hover:bg-emerald-100 transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Approve PO</span>
                    <span className="text-xs text-emerald-600 font-bold">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('reject_po', execActionTarget);
                      setExecActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-rose-200 bg-rose-50/50 px-4 py-2.5 text-left text-sm font-medium text-rose-700 hover:bg-rose-100 transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Reject PO</span>
                    <span className="text-xs text-rose-400">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('request_clarification', execActionTarget);
                      setExecActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-purple-200 bg-purple-50/50 px-4 py-2.5 text-left text-sm font-medium text-purple-700 hover:bg-purple-100 transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Request Clarification</span>
                    <span className="text-xs text-purple-400">→</span>
                  </button>
                  {execActionTarget.approval_status === 'Clarification Requested' && (
                    <button
                      type="button"
                      onClick={() => {
                        onAction?.('reply_clarification', execActionTarget);
                        setExecActionTarget(null);
                      }}
                      className="w-full rounded-lg border border-indigo-200 bg-indigo-50/50 px-4 py-2.5 text-left text-sm font-medium text-indigo-700 hover:bg-indigo-100 transition-colors flex items-center justify-between shadow-sm"
                    >
                      <span>Reply Clarification & Resubmit</span>
                      <span className="text-xs text-indigo-400">→</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Active Purchase Orders Queue Table */}
      <div className="card p-4">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Active Purchase Orders</h3>
          <div className="flex flex-wrap gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => setActivePoApprovalFilter('All')}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${activePoApprovalFilter === 'All' ? 'bg-slate-800 text-white font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              All ({countActiveAll})
            </button>
            {countActiveApproved > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter('Approved')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${activePoApprovalFilter === 'Approved' ? 'bg-emerald-100 text-emerald-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                Approved ({countActiveApproved})
              </button>
            )}
            {countActiveIssued > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter('Issued')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${activePoApprovalFilter === 'Issued' ? 'bg-blue-100 text-blue-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                Issued ({countActiveIssued})
              </button>
            )}
            {countActivePending > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter('Pending Approval')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${activePoApprovalFilter === 'Pending Approval' ? 'bg-amber-100 text-amber-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                Pending ({countActivePending})
              </button>
            )}
            {countActiveCancelled > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter('Cancelled')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${activePoApprovalFilter === 'Cancelled' ? 'bg-rose-100 text-rose-800 font-semibold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                Cancelled ({countActiveCancelled})
              </button>
            )}
          </div>
        </div>
        {filteredActivePos.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-400">No active POs matching approval state "{activePoApprovalFilter}".</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-surface-border bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-slate-50/80 text-xs font-semibold text-slate-500">
                  <th className="px-3 py-2.5 text-left font-medium">PO Number</th>
                  <th className="px-3 py-2.5 text-left font-medium">Vendor</th>
                  <th className="px-3 py-2.5 text-left font-medium leading-tight">
                    <div>Order</div>
                    <div>Date</div>
                  </th>
                  <th className="px-3 py-2.5 text-left font-medium leading-tight">
                    <div>Expected</div>
                    <div>Delivery</div>
                  </th>
                  <th className="px-3 py-2.5 pr-8 text-right font-medium">Total Amount</th>
                  <th className="px-3 py-2.5 text-center font-medium">Fulfillment</th>
                  <th className="px-3 py-2.5 text-center font-medium">Approval</th>
                  <th className="px-3 py-2.5 text-center font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filteredActivePos.map((po) => {
                  const overdue = new Date(po.expected_delivery) < new Date() && po.fulfillment_status !== 'Fully Received & Billed';
                  return (
                    <tr key={po.po_number} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-3 py-2.5 font-mono text-xs font-medium text-slate-800">{po.po_number}</td>
                      <td className="px-3 py-2.5 font-medium text-slate-800">{po.vendor}</td>
                      <td className="px-3 py-2.5 text-slate-600">{po.order_date}</td>
                      <td className={`px-3 py-2.5 text-slate-600 ${overdue ? 'font-semibold text-rose-600' : ''}`}>
                        {po.expected_delivery}{overdue ? ' ⚠' : ''}
                      </td>
                      <td className="px-3 py-2.5 pr-8 text-right font-semibold text-slate-900">RM {po.total_amount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${FULFILLMENT_STYLE[po.fulfillment_status] ?? 'bg-slate-100 text-slate-600'}`}>
                          {po.fulfillment_status}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${APPROVAL_STYLE[po.approval_status] ?? 'bg-slate-100 text-slate-600'}`}>
                          {po.approval_status}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <button
                          type="button"
                          onClick={() => setPoActionTarget(po)}
                          className="rounded-md bg-brand px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:opacity-90 transition-opacity"
                        >
                          Action
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* PO Action Modal Dialog */}
      {poActionTarget && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default bg-black/30" onClick={() => setPoActionTarget(null)} aria-label="Close" />
          <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16" onClick={() => setPoActionTarget(null)}>
            <div className="card relative z-50 w-full max-w-md overflow-hidden bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">PO Action</h2>
                  <p className="text-xs text-slate-500">{poActionTarget.vendor} · {poActionTarget.po_number}</p>
                </div>
                <button type="button" onClick={() => setPoActionTarget(null)} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 px-5 py-4 bg-slate-50/50">
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">PO Total Amount</div>
                  <div className="text-base font-bold text-slate-900">RM {poActionTarget.total_amount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">Expected Delivery</div>
                  <div className="text-base font-bold text-indigo-700">{poActionTarget.expected_delivery}</div>
                </div>
              </div>

              <div className="border-t border-surface-border px-5 py-4">
                <p className="mb-3 text-xs text-slate-500 font-medium">Select action to send to Chotatsu (Procurement Agent):</p>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('receive_grn', poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-surface-border bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:border-brand hover:text-brand transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Receive Goods (GRN)</span>
                    <span className="text-xs text-slate-400">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('sync_bill', poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-surface-border bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:border-brand hover:text-brand transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Sync Bill to Accounting</span>
                    <span className="text-xs text-slate-400">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('send_reminder', poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-surface-border bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:border-brand hover:text-brand transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Send Delivery Reminder to Vendor</span>
                    <span className="text-xs text-slate-400">→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.('cancel_po', poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="w-full rounded-lg border border-rose-200 bg-rose-50/50 px-4 py-2.5 text-left text-sm font-medium text-rose-700 hover:bg-rose-100 transition-colors flex items-center justify-between shadow-sm"
                  >
                    <span>Cancel Purchase Order</span>
                    <span className="text-xs text-rose-400">→</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Vendor Scorecard & Spend Concentration */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Vendor Scorecard & SLA Ratings</h3>
          {stats.vendorScorecard.length === 0 ? (
            <p className="text-sm text-slate-400">No vendor scorecard data available yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-border text-xs text-slate-500">
                    <th className="pb-2 text-left font-medium">Vendor Name</th>
                    <th className="pb-2 text-right font-medium">YTD Spend</th>
                    <th className="pb-2 text-right font-medium">On-Time</th>
                    <th className="pb-2 text-right font-medium">Quality</th>
                    <th className="pb-2 text-center font-medium">SLA Rating</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {stats.vendorScorecard.map((v) => (
                    <tr key={v.vendor} className="hover:bg-surface-muted/50">
                      <td className="py-2 font-medium text-slate-800">{v.vendor}</td>
                      <td className="py-2 text-right font-semibold text-slate-900">RM {v.ytd_spend.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                      <td className={`py-2 text-right font-medium ${v.on_time_delivery_rate >= 90 ? 'text-emerald-600' : v.on_time_delivery_rate >= 75 ? 'text-amber-600' : 'text-rose-600'}`}>
                        {v.on_time_delivery_rate.toFixed(0)}%
                      </td>
                      <td className={`py-2 text-right font-medium ${v.quality_acceptance_rate >= 95 ? 'text-emerald-600' : v.quality_acceptance_rate >= 85 ? 'text-amber-600' : 'text-rose-600'}`}>
                        {v.quality_acceptance_rate.toFixed(0)}%
                      </td>
                      <td className="py-2 text-center">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${SLA_STYLE[v.sla_status] ?? 'bg-slate-100 text-slate-600'}`}>
                          {v.sla_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Vendor Spend Concentration Donut */}
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Vendor Spend Concentration</h3>
          {concentrationAlert && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {concentrationAlert.vendor} represents {concentrationAlert.spend_pct.toFixed(1)}% of spend — supplier dependency risk (&gt;25%)
            </div>
          )}
          {stats.vendorSpendConcentration.length === 0 ? (
            <p className="text-sm text-slate-400">No vendor spend data available yet.</p>
          ) : (
            <div>
              <PieChart
                data={[...stats.vendorSpendConcentration]
                  .sort((a, b) => (b.spend ?? 0) - (a.spend ?? 0))
                  .map((v) => ({ name: v.vendor, value: v.spend }))}
                color={color}
                unit="RM "
                height={200}
                innerRadius={45}
                showLegend={false}
              />
              <div className="mt-3 divide-y divide-surface-border border-t border-surface-border pt-2">
                {[...stats.vendorSpendConcentration]
                  .sort((a, b) => (b.spend ?? 0) - (a.spend ?? 0))
                  .map((v, i) => {
                    const colors = chartColors(color, stats.vendorSpendConcentration.length);
                    return (
                      <div key={v.vendor} className="flex items-center justify-between py-1.5 text-xs">
                        <div className="flex items-center gap-2 truncate pr-2">
                          <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: colors[i % colors.length] }} />
                          <span className="font-medium text-slate-800 truncate">{v.vendor}</span>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <span className="font-semibold text-slate-900">RM {v.spend.toLocaleString()}</span>
                          <span className="w-12 text-right font-mono font-medium text-slate-500">{v.spend_pct.toFixed(1)}%</span>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

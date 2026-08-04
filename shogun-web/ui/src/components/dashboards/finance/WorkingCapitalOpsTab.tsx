import { useState } from 'react';
import { X } from 'lucide-react';
import type { DunningItem, FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmtMyr = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const BUCKET_STYLE: Record<string, string> = {
  '0-30':  'bg-emerald-100 text-emerald-700',
  '31-60': 'bg-amber-100 text-amber-700',
  '61-90': 'bg-orange-100 text-orange-700',
  '90+':   'bg-rose-100 text-rose-700',
};

const MATCH_STYLE: Record<string, string> = {
  'Matched':     'bg-emerald-100 text-emerald-700',
  'PO Mismatch': 'bg-amber-100 text-amber-700',
  'Missing GRN': 'bg-rose-100 text-rose-700',
};

const APPROVAL_STYLE: Record<string, string> = {
  'Pending':           'bg-slate-100 text-slate-600',
  'Approved':          'bg-emerald-100 text-emerald-700',
  'Paid':              'bg-blue-100 text-blue-700',
  'On Hold':           'bg-rose-100 text-rose-700',
};

export function WorkingCapitalOpsTab({ stats }: Props) {
  const [dunningTarget, setDunningTarget] = useState<DunningItem | null>(null);

  const ag = stats.arAging;
  const agTotal = ag.bucket_0_30 + ag.bucket_31_60 + ag.bucket_61_90 + ag.bucket_90_plus;
  const pct = (n: number) => agTotal > 0 ? (n / agTotal) * 100 : 0;

  const WC_METRICS = [
    { label: 'Total AR', value: fmtMyr(stats.totalAR) },
    { label: 'AR Overdue >30d', value: fmtMyr(stats.arOverdue30), warn: stats.arOverdue30 > 0 },
    { label: 'DSO (days)', value: stats.dso > 0 ? `${stats.dso.toFixed(0)}d` : '—' },
    { label: 'Total AP', value: fmtMyr(stats.totalAP) },
    { label: 'AP Overdue', value: fmtMyr(stats.apOverdue), warn: stats.apOverdue > 0 },
    { label: 'DPO (days)', value: stats.dpo > 0 ? `${stats.dpo.toFixed(0)}d` : '—' },
  ];

  return (
    <div className="space-y-4">
      {/* Working Capital Metric Strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {WC_METRICS.map((m) => (
          <div key={m.label} className="card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{m.label}</div>
            <div className={`mt-1 text-lg font-bold ${m.warn ? 'text-rose-600' : 'text-slate-900'}`}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* AR Aging */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">AR Aging Distribution</h3>
        <div className="mb-4 space-y-2">
          {[
            { label: '0–30 days', val: ag.bucket_0_30, key: '0-30' },
            { label: '31–60 days', val: ag.bucket_31_60, key: '31-60' },
            { label: '61–90 days', val: ag.bucket_61_90, key: '61-90' },
            { label: '90+ days', val: ag.bucket_90_plus, key: '90+' },
          ].map((b) => (
            <div key={b.key} className="flex items-center gap-3">
              <div className="w-20 shrink-0 text-xs text-slate-500">{b.label}</div>
              <div className="flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-2 rounded-full transition-all ${
                    b.key === '0-30' ? 'bg-emerald-500' :
                    b.key === '31-60' ? 'bg-amber-400' :
                    b.key === '61-90' ? 'bg-orange-500' : 'bg-rose-500'
                  }`}
                  style={{ width: `${pct(b.val)}%` }}
                />
              </div>
              <div className="w-24 text-right text-xs font-semibold text-slate-700">{fmtMyr(b.val)}</div>
            </div>
          ))}
        </div>

        {/* Dunning Queue Table */}
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Dunning Queue</div>
        {stats.dunningQueue.length === 0 ? (
          <p className="text-sm text-slate-400">No overdue invoices requiring action.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">Customer</th>
                  <th className="pb-2 text-left font-medium">Invoice #</th>
                  <th className="pb-2 text-left font-medium">Due Date</th>
                  <th className="pb-2 text-right font-medium">Amount</th>
                  <th className="pb-2 text-center font-medium">Bucket</th>
                  <th className="pb-2 text-left font-medium">Status</th>
                  <th className="pb-2 text-center font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.dunningQueue.map((item) => (
                  <tr key={item.invoice_no} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-medium text-slate-800">{item.customer}</td>
                    <td className="py-2 text-slate-600">{item.invoice_no}</td>
                    <td className="py-2 text-slate-600">{item.due_date}</td>
                    <td className="py-2 text-right font-semibold text-slate-900">{fmtMyr(item.amount)}</td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${BUCKET_STYLE[item.bucket] ?? 'bg-slate-100 text-slate-600'}`}>
                        {item.bucket}d
                      </span>
                    </td>
                    <td className="py-2 text-xs text-slate-600">{item.dunning_status}</td>
                    <td className="py-2 text-center">
                      <button
                        type="button"
                        onClick={() => setDunningTarget(item)}
                        className="rounded-md bg-brand px-2.5 py-1 text-xs font-medium text-white hover:opacity-90 transition-opacity"
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

      {/* AP 3-Way Match & Payment Queue */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">AP 3-Way Match & Payment Run Queue</h3>
        {stats.apBills.length === 0 ? (
          <p className="text-sm text-slate-400">No AP bills pending.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">Vendor</th>
                  <th className="pb-2 text-left font-medium">Bill #</th>
                  <th className="pb-2 text-left font-medium">Due Date</th>
                  <th className="pb-2 text-right font-medium">Amount</th>
                  <th className="pb-2 text-center font-medium">3-Way Match</th>
                  <th className="pb-2 text-center font-medium">Approval</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.apBills.map((bill) => (
                  <tr key={bill.bill_no} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-medium text-slate-800">{bill.vendor}</td>
                    <td className="py-2 text-slate-600">{bill.bill_no}</td>
                    <td className="py-2 text-slate-600">{bill.due_date}</td>
                    <td className="py-2 text-right font-semibold text-slate-900">{fmtMyr(bill.amount)}</td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${MATCH_STYLE[bill.match_status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {bill.match_status}
                      </span>
                    </td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${APPROVAL_STYLE[bill.approval_status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {bill.approval_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Dunning Action Modal */}
      {dunningTarget && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default bg-black/30" onClick={() => setDunningTarget(null)} aria-label="Close" />
          <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16" onClick={() => setDunningTarget(null)}>
            <div className="card relative z-50 w-full max-w-md overflow-hidden" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Dunning Action</h2>
                  <p className="text-xs text-slate-500">{dunningTarget.customer} · {dunningTarget.invoice_no}</p>
                </div>
                <button type="button" onClick={() => setDunningTarget(null)} className="btn-ghost !px-2 !py-1" aria-label="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 px-5 py-4">
                <div className="rounded-lg bg-surface-muted p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">Amount Due</div>
                  <div className="text-base font-bold text-slate-900">{fmtMyr(dunningTarget.amount)}</div>
                </div>
                <div className="rounded-lg bg-surface-muted p-3 text-center">
                  <div className="text-xs font-medium text-slate-500">Overdue Days</div>
                  <div className="text-base font-bold text-rose-600">{dunningTarget.aging_days}d</div>
                </div>
              </div>
              <div className="border-t border-surface-border px-5 py-4">
                <p className="mb-3 text-xs text-slate-500">Select action to send to Koku (Finance Agent):</p>
                <div className="space-y-2">
                  {['Send Reminder Email', 'Escalate to Sales', 'Flag for Legal Notice', 'Log Call Note'].map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => setDunningTarget(null)}
                      className="w-full rounded-lg border border-surface-border bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:border-brand hover:text-brand transition-colors"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

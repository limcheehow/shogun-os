import { Check, Circle } from 'lucide-react';
import type { FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmtMyr = (n: number) =>
  n >= 1_000_000 ? `RM ${(n / 1_000_000).toFixed(2)}M` : `RM ${(n / 1_000).toFixed(0)}K`;

const STATUS_STYLE: Record<string, string> = {
  Pending:   'bg-slate-100 text-slate-600',
  Submitted: 'bg-emerald-100 text-emerald-700',
  Overdue:   'bg-rose-100 text-rose-700',
};

const AUDIT_STYLE: Record<string, string> = {
  Approved:  'bg-emerald-100 text-emerald-700',
  Flagged:   'bg-amber-100 text-amber-700',
  Rejected:  'bg-rose-100 text-rose-700',
};

export function CloseTaxComplianceTab({ stats, color }: Props) {
  const completed = stats.closeChecklist.filter((t) => t.completed).length;
  const total = stats.closeChecklist.length;
  const progressPct = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Month-End Close Checklist */}
      <div className="card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Month-End Period Close Checklist</h3>
          <span className="text-xs text-slate-500">{completed}/{total} completed</span>
        </div>
        <div className="mb-4 h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-2 rounded-full transition-all"
            style={{ width: `${progressPct}%`, backgroundColor: color }}
          />
        </div>
        <div className="space-y-2">
          {stats.closeChecklist.map((item) => (
            <div key={item.id} className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-surface-muted/50">
              <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${item.completed ? 'bg-emerald-500' : 'border-2 border-slate-300'}`}>
                {item.completed ? <Check className="h-3 w-3 text-white" /> : <Circle className="h-2 w-2 text-slate-300" />}
              </div>
              <span className={`text-sm ${item.completed ? 'text-slate-400 line-through' : 'text-slate-700 font-medium'}`}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Malaysian Statutory Hub */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Statutory Filing Calendar */}
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Statutory Remittance Calendar</h3>
          <p className="mb-3 text-xs text-slate-400">EPF (KWSP) · SOCSO (PERKESO) · EIS · LHDN PCB</p>
          {stats.statutorySchedule.length === 0 ? (
            <p className="text-sm text-slate-400">No statutory schedule synced yet. Koku generates this from payroll data.</p>
          ) : (
            <div className="space-y-2">
              {stats.statutorySchedule.map((item) => (
                <div key={item.name} className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{item.name}</div>
                    <div className="text-xs text-slate-500">Due: {item.due_date}{item.amount ? ` · ${fmtMyr(item.amount)}` : ''}</div>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[item.status] ?? 'bg-slate-100 text-slate-600'}`}>
                    {item.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* SST-02 Readiness */}
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">SST-02 Return Readiness</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2">
              <span className="text-sm text-slate-600">Draft Status</span>
              <span className="text-sm font-semibold text-slate-800">{stats.sstReadiness.draft_status}</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2">
              <span className="text-sm text-slate-600">Taxable Sales</span>
              <span className="text-sm font-semibold text-slate-800">{fmtMyr(stats.sstReadiness.taxable_sales)}</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2">
              <span className="text-sm text-slate-600">SST Liability</span>
              <span className="text-sm font-bold text-rose-600">{fmtMyr(stats.sstReadiness.sst_liability)}</span>
            </div>
          </div>

          {/* CP58 Register */}
          {stats.cp58Register.length > 0 && (
            <>
              <h3 className="mb-2 mt-4 text-sm font-semibold text-slate-700">CP58 Contractor Register</h3>
              <div className="space-y-2">
                {stats.cp58Register.slice(0, 4).map((c) => (
                  <div key={c.ic_or_reg} className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2">
                    <div>
                      <div className="text-xs font-medium text-slate-800">{c.contractor_name}</div>
                      <div className="text-xs text-slate-500">{c.ic_or_reg}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-semibold text-slate-800">{fmtMyr(c.total_paid_ytd)}</div>
                      {c.threshold_exceeded && (
                        <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-700">⚠ CP58 Required</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* WHT Queue */}
      {stats.whtQueue.length > 0 && (
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Withholding Tax Queue (Sec 107A / 109B)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">Foreign Vendor</th>
                  <th className="pb-2 text-left font-medium">Country</th>
                  <th className="pb-2 text-right font-medium">Payment Amt</th>
                  <th className="pb-2 text-right font-medium">WHT Rate</th>
                  <th className="pb-2 text-right font-medium">WHT Amount</th>
                  <th className="pb-2 text-left font-medium">Section</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.whtQueue.map((w) => (
                  <tr key={`${w.vendor}-${w.section}`} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-medium text-slate-800">{w.vendor}</td>
                    <td className="py-2 text-slate-600">{w.country}</td>
                    <td className="py-2 text-right text-slate-700">{fmtMyr(w.payment_amount)}</td>
                    <td className="py-2 text-right text-slate-700">{w.wht_rate}%</td>
                    <td className="py-2 text-right font-semibold text-rose-600">{fmtMyr(w.wht_amount)}</td>
                    <td className="py-2 text-xs text-slate-500">{w.section}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Expense Claim AI Audit */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Expense Claim AI Audit Queue</h3>
        {stats.expenseClaimAudit.length === 0 ? (
          <p className="text-sm text-slate-400">No expense claims pending audit.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">Employee</th>
                  <th className="pb-2 text-left font-medium">Category</th>
                  <th className="pb-2 text-left font-medium">Date</th>
                  <th className="pb-2 text-right font-medium">Amount</th>
                  <th className="pb-2 text-center font-medium">Receipt</th>
                  <th className="pb-2 text-center font-medium">SST OK</th>
                  <th className="pb-2 text-center font-medium">Policy</th>
                  <th className="pb-2 text-center font-medium">Audit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.expenseClaimAudit.map((claim, i) => (
                  <tr key={i} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-medium text-slate-800">{claim.employee}</td>
                    <td className="py-2 text-slate-600">{claim.category}</td>
                    <td className="py-2 text-slate-600">{claim.claim_date}</td>
                    <td className="py-2 text-right font-semibold text-slate-900">{fmtMyr(claim.amount)}</td>
                    <td className="py-2 text-center">{claim.receipt_attached ? '✓' : <span className="text-rose-500">✗</span>}</td>
                    <td className="py-2 text-center">{claim.sst_compliant ? '✓' : <span className="text-rose-500">✗</span>}</td>
                    <td className="py-2 text-center">{claim.policy_exceeded ? <span className="text-rose-500">⚠</span> : '✓'}</td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${AUDIT_STYLE[claim.audit_status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {claim.audit_status}
                      </span>
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

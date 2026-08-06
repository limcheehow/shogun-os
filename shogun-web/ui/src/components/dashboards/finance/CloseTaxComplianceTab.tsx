import { Check, Circle } from 'lucide-react';
import type { FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmtMyr = (n: number) =>
  n >= 1_000_000 ? `RM ${(n / 1_000_000).toFixed(2)}M` : `RM ${(n / 1_000).toFixed(0)}K`;

const STATUS_CHIP: Record<string, string> = {
  Pending:   'muted',
  Submitted: 'ok',
  Overdue:   'bad',
};

const AUDIT_CHIP: Record<string, string> = {
  Approved:  'ok',
  Flagged:   'warn',
  Rejected:  'bad',
};

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="pb-2" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function CloseTaxComplianceTab({ stats, color }: Props) {
  const completed = stats.closeChecklist.filter((t) => t.completed).length;
  const total = stats.closeChecklist.length;
  const progressPct = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="sd-stack">
      <div className="sd-chart-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
          <h3 className="sd-chart-title" style={{ marginBottom: 0 }}>Month-End Period Close Checklist</h3>
          <span style={{ fontSize: '0.75rem', color: MUTED }}>{completed}/{total} completed</span>
        </div>
        <div style={{ height: '0.5rem', borderRadius: 999, overflow: 'hidden', background: SURFACE_2, marginBottom: '0.75rem' }}>
          <div style={{ height: '100%', width: `${progressPct}%`, borderRadius: 999, background: color }} />
        </div>
        <div className="sd-stack" style={{ gap: '0.3rem' }}>
          {stats.closeChecklist.map((item) => (
            <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderRadius: '0.5rem', padding: '0.4rem 0.6rem', background: SURFACE_2 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '1.25rem', height: '1.25rem', borderRadius: 999, background: item.completed ? 'var(--samurai-ok)' : 'transparent', border: item.completed ? 'none' : `2px solid ${BORDER}` }}>
                {item.completed ? <Check className="h-3 w-3" style={{ color: '#070b14' }} /> : <Circle className="h-2 w-2" style={{ color: MUTED }} />}
              </div>
              <span style={{ fontSize: '0.85rem', color: item.completed ? MUTED : TEXT, fontWeight: item.completed ? 400 : 500, textDecoration: item.completed ? 'line-through' : 'none' }}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="sd-row">
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Statutory Remittance Calendar</h3>
          <p className="sd-chart-sub">EPF (KWSP) · SOCSO (PERKESO) · EIS · LHDN PCB</p>
          {stats.statutorySchedule.length === 0 ? (
            <p style={{ fontSize: '0.85rem', color: MUTED }}>No statutory schedule synced yet. Koku generates this from payroll data.</p>
          ) : (
            <div className="sd-stack" style={{ gap: '0.4rem' }}>
              {stats.statutorySchedule.map((item) => (
                <div key={item.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '0.5rem', background: SURFACE_2, padding: '0.5rem 0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: TEXT }}>{item.name}</div>
                    <div style={{ fontSize: '0.72rem', color: MUTED }}>Due: {item.due_date}{item.amount ? ` · ${fmtMyr(item.amount)}` : ''}</div>
                  </div>
                  <span className={`sd-chip ${STATUS_CHIP[item.status] ?? 'muted'}`}>{item.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="sd-chart-card">
          <h3 className="sd-chart-title">SST-02 Return Readiness</h3>
          <p className="sd-chart-sub">Malaysian SST draft &amp; liability</p>
          <div className="sd-stack" style={{ gap: '0.4rem', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '0.5rem', background: SURFACE_2, padding: '0.5rem 0.75rem' }}>
              <span style={{ fontSize: '0.85rem', color: MUTED }}>Draft Status</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 500, color: TEXT }}>{stats.sstReadiness.draft_status}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '0.5rem', background: SURFACE_2, padding: '0.5rem 0.75rem' }}>
              <span style={{ fontSize: '0.85rem', color: MUTED }}>Taxable Sales</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 500, color: TEXT }}>{fmtMyr(stats.sstReadiness.taxable_sales)}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '0.5rem', background: SURFACE_2, padding: '0.5rem 0.75rem' }}>
              <span style={{ fontSize: '0.85rem', color: MUTED }}>SST Liability</span>
              <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.95rem', fontWeight: 600, color: 'var(--samurai-danger)' }}>{fmtMyr(stats.sstReadiness.sst_liability)}</span>
            </div>
          </div>

          {stats.cp58Register.length > 0 && (
            <>
              <div className="sd-kpi-label" style={{ marginTop: '0.5rem', marginBottom: '0.4rem' }}>CP58 Contractor Register</div>
              <div className="sd-stack" style={{ gap: '0.4rem' }}>
                {stats.cp58Register.slice(0, 4).map((c) => (
                  <div key={c.ic_or_reg} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '0.5rem', background: SURFACE_2, padding: '0.5rem 0.75rem' }}>
                    <div>
                      <div style={{ fontSize: '0.78rem', fontWeight: 500, color: TEXT }}>{c.contractor_name}</div>
                      <div style={{ fontSize: '0.72rem', color: MUTED }}>{c.ic_or_reg}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: TEXT }}>{fmtMyr(c.total_paid_ytd)}</div>
                      {c.threshold_exceeded && <span className="sd-chip warn">⚠ CP58 Required</span>}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {stats.whtQueue.length > 0 && (
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Withholding Tax Queue (Sec 107A / 109B)</h3>
          <p className="sd-chart-sub">Foreign vendor payments subject to WHT</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Foreign Vendor</Th>
                  <Th align="left">Country</Th>
                  <Th align="right">Payment Amt</Th>
                  <Th align="right">WHT Rate</Th>
                  <Th align="right">WHT Amount</Th>
                  <Th align="left">Section</Th>
                </tr>
              </thead>
              <tbody>
                {stats.whtQueue.map((w) => (
                  <tr key={`${w.vendor}-${w.section}`} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="py-2" style={{ fontWeight: 600, color: TEXT }}>{w.vendor}</td>
                    <td className="py-2" style={{ color: MUTED }}>{w.country}</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{fmtMyr(w.payment_amount)}</td>
                    <td className="py-2 text-right" style={{ color: TEXT }}>{w.wht_rate}%</td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: 'var(--samurai-danger)' }}>{fmtMyr(w.wht_amount)}</td>
                    <td className="py-2" style={{ fontSize: '0.75rem', color: MUTED }}>{w.section}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Expense Claim AI Audit Queue</h3>
        <p className="sd-chart-sub">Receipt, SST, and policy checks by Koku</p>
        {stats.expenseClaimAudit.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: MUTED }}>No expense claims pending audit.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Employee</Th>
                  <Th align="left">Category</Th>
                  <Th align="left">Date</Th>
                  <Th align="right">Amount</Th>
                  <Th align="center">Receipt</Th>
                  <Th align="center">SST OK</Th>
                  <Th align="center">Policy</Th>
                  <Th align="center">Audit</Th>
                </tr>
              </thead>
              <tbody>
                {stats.expenseClaimAudit.map((claim, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="py-2" style={{ fontWeight: 600, color: TEXT }}>{claim.employee}</td>
                    <td className="py-2" style={{ color: MUTED }}>{claim.category}</td>
                    <td className="py-2" style={{ color: MUTED }}>{claim.claim_date}</td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: TEXT }}>{fmtMyr(claim.amount)}</td>
                    <td className="py-2 text-center" style={{ color: claim.receipt_attached ? TEXT : 'var(--samurai-danger)' }}>{claim.receipt_attached ? '✓' : '✗'}</td>
                    <td className="py-2 text-center" style={{ color: claim.sst_compliant ? TEXT : 'var(--samurai-danger)' }}>{claim.sst_compliant ? '✓' : '✗'}</td>
                    <td className="py-2 text-center" style={{ color: claim.policy_exceeded ? 'var(--samurai-danger)' : TEXT }}>{claim.policy_exceeded ? '⚠' : '✓'}</td>
                    <td className="py-2 text-center">
                      <span className={`sd-chip ${AUDIT_CHIP[claim.audit_status] ?? 'muted'}`}>{claim.audit_status}</span>
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
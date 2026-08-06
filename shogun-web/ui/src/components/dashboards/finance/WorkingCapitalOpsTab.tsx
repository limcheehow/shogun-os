import { useState } from 'react';
import { X } from 'lucide-react';
import type { DunningItem, FinanceDashboardStats } from '../../../lib/types';

interface Props { stats: FinanceDashboardStats; color: string }

const fmtMyr = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const BUCKET_CHIP: Record<string, string> = {
  '0-30':  'ok',
  '31-60': 'warn',
  '61-90': 'warn',
  '90+':   'bad',
};

const MATCH_CHIP: Record<string, string> = {
  'Matched':     'ok',
  'PO Mismatch': 'warn',
  'Missing GRN': 'bad',
};

const APPROVAL_CHIP: Record<string, string> = {
  'Pending':  'muted',
  'Approved': 'ok',
  'Paid':     'ok',
  'On Hold':  'bad',
};

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';
const HOVER = 'var(--samurai-hover-ui)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
const tdMuted = { color: MUTED } as const;

function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="pb-2" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function WorkingCapitalOpsTab({ stats }: Props) {
  const [dunningTarget, setDunningTarget] = useState<DunningItem | null>(null);

  const ag = stats.arAging;
  const agTotal = ag.bucket_0_30 + ag.bucket_31_60 + ag.bucket_61_90 + ag.bucket_90_plus;
  const pct = (n: number) => agTotal > 0 ? (n / agTotal) * 100 : 0;

  const WC_METRICS = [
    { label: 'Total AR', value: fmtMyr(stats.totalAR), warn: false },
    { label: 'AR Overdue >30d', value: fmtMyr(stats.arOverdue30), warn: stats.arOverdue30 > 0 },
    { label: 'DSO (days)', value: stats.dso > 0 ? `${stats.dso.toFixed(0)}d` : '—', warn: false },
    { label: 'Total AP', value: fmtMyr(stats.totalAP), warn: false },
    { label: 'AP Overdue', value: fmtMyr(stats.apOverdue), warn: stats.apOverdue > 0 },
    { label: 'DPO (days)', value: stats.dpo > 0 ? `${stats.dpo.toFixed(0)}d` : '—', warn: false },
  ];

  return (
    <div className="sd-stack">
      <div className="sd-kpi-grid">
        {WC_METRICS.map((m) => (
          <div key={m.label} className="sd-kpi-card">
            <div className="sd-kpi-label">{m.label}</div>
            <div className="sd-kpi-value" style={{ color: m.warn ? 'var(--samurai-danger)' : TEXT }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div className="sd-chart-card">
        <h3 className="sd-chart-title">AR Aging Distribution</h3>
        <p className="sd-chart-sub">Outstanding receivables by aging bucket</p>
        <div className="sd-stack" style={{ gap: '0.5rem', marginBottom: '1rem' }}>
          {[
            { label: '0–30 days', val: ag.bucket_0_30, key: '0-30', color: 'var(--samurai-ok)' },
            { label: '31–60 days', val: ag.bucket_31_60, key: '31-60', color: 'var(--samurai-warning)' },
            { label: '61–90 days', val: ag.bucket_61_90, key: '61-90', color: '#f59e0b' },
            { label: '90+ days', val: ag.bucket_90_plus, key: '90+', color: 'var(--samurai-danger)' },
          ].map((b) => (
            <div key={b.key} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ width: '5rem', flexShrink: 0, fontSize: '0.75rem', color: MUTED }}>{b.label}</div>
              <div style={{ flex: 1, height: '0.5rem', borderRadius: 999, overflow: 'hidden', background: SURFACE_2 }}>
                <div style={{ height: '100%', width: `${pct(b.val)}%`, borderRadius: 999, background: b.color }} />
              </div>
              <div style={{ width: '6rem', textAlign: 'right', fontSize: '0.75rem', fontWeight: 600, color: TEXT }}>{fmtMyr(b.val)}</div>
            </div>
          ))}
        </div>

        <div className="sd-kpi-label" style={{ marginBottom: '0.5rem' }}>Dunning Queue</div>
        {stats.dunningQueue.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: MUTED }}>No overdue invoices requiring action.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Customer</Th>
                  <Th align="left">Invoice #</Th>
                  <Th align="left">Due Date</Th>
                  <Th align="right">Amount</Th>
                  <Th align="center">Bucket</Th>
                  <Th align="left">Status</Th>
                  <Th align="center">Action</Th>
                </tr>
              </thead>
              <tbody>
                {stats.dunningQueue.map((item) => (
                  <tr key={item.invoice_no} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="py-2" style={{ fontWeight: 600, color: TEXT }}>{item.customer}</td>
                    <td className="py-2" style={tdMuted}>{item.invoice_no}</td>
                    <td className="py-2" style={tdMuted}>{item.due_date}</td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: TEXT }}>{fmtMyr(item.amount)}</td>
                    <td className="py-2 text-center">
                      <span className={`sd-chip ${BUCKET_CHIP[item.bucket] ?? 'muted'}`}>{item.bucket}d</span>
                    </td>
                    <td className="py-2" style={{ fontSize: '0.75rem', color: MUTED }}>{item.dunning_status}</td>
                    <td className="py-2 text-center">
                      <button
                        type="button"
                        onClick={() => setDunningTarget(item)}
                        className="sd-btn sd-btn-secondary"
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}
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

      <div className="sd-chart-card">
        <h3 className="sd-chart-title">AP 3-Way Match &amp; Payment Run Queue</h3>
        <p className="sd-chart-sub">Vendor bills pending match and approval</p>
        {stats.apBills.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: MUTED }}>No AP bills pending.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Vendor</Th>
                  <Th align="left">Bill #</Th>
                  <Th align="left">Due Date</Th>
                  <Th align="right">Amount</Th>
                  <Th align="center">3-Way Match</Th>
                  <Th align="center">Approval</Th>
                </tr>
              </thead>
              <tbody>
                {stats.apBills.map((bill) => (
                  <tr key={bill.bill_no} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="py-2" style={{ fontWeight: 600, color: TEXT }}>{bill.vendor}</td>
                    <td className="py-2" style={tdMuted}>{bill.bill_no}</td>
                    <td className="py-2" style={tdMuted}>{bill.due_date}</td>
                    <td className="py-2 text-right" style={{ fontWeight: 600, color: TEXT }}>{fmtMyr(bill.amount)}</td>
                    <td className="py-2 text-center">
                      <span className={`sd-chip ${MATCH_CHIP[bill.match_status] ?? 'muted'}`}>{bill.match_status}</span>
                    </td>
                    <td className="py-2 text-center">
                      <span className={`sd-chip ${APPROVAL_CHIP[bill.approval_status] ?? 'muted'}`}>{bill.approval_status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {dunningTarget && (
        <>
          <button type="button" style={{ position: 'fixed', inset: 0, zIndex: 40, background: 'rgba(0,0,0,0.4)', border: 'none', cursor: 'default' }} onClick={() => setDunningTarget(null)} aria-label="Close" />
          <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', justifyContent: 'center', padding: '1rem', paddingTop: '4rem' }} onClick={() => setDunningTarget(null)}>
            <div className="sd-card" style={{ position: 'relative', zIndex: 50, width: '100%', maxWidth: '28rem' }} onClick={(e) => e.stopPropagation()}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.75rem', marginBottom: '0.75rem' }}>
                <div>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: TEXT, margin: 0 }}>Dunning Action</h2>
                  <p style={{ fontSize: '0.72rem', color: MUTED, margin: 0 }}>{dunningTarget.customer} · {dunningTarget.invoice_no}</p>
                </div>
                <button type="button" className="sd-icon-btn" onClick={() => setDunningTarget(null)} aria-label="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <div style={{ borderRadius: '0.5rem', background: SURFACE_2, padding: '0.6rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: MUTED }}>Amount Due</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, color: TEXT }}>{fmtMyr(dunningTarget.amount)}</div>
                </div>
                <div style={{ borderRadius: '0.5rem', background: SURFACE_2, padding: '0.6rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: MUTED }}>Overdue Days</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, color: 'var(--samurai-danger)' }}>{dunningTarget.aging_days}d</div>
                </div>
              </div>
              <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: '0.75rem' }}>
                <p style={{ fontSize: '0.72rem', color: MUTED, marginBottom: '0.6rem' }}>Select action to send to Koku (Finance Agent):</p>
                <div className="sd-stack" style={{ gap: '0.4rem' }}>
                  {['Send Reminder Email', 'Escalate to Sales', 'Flag for Legal Notice', 'Log Call Note'].map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => setDunningTarget(null)}
                      className="sd-btn sd-btn-secondary"
                      style={{ justifyContent: 'flex-start', fontWeight: 500 }}
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
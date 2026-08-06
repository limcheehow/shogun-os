import { useState } from 'react';
import { Award, Zap, ShieldCheck, Upload, FileText } from 'lucide-react';
import type { ProcurementDashboardStats, RfqComparison } from '../../../lib/types';

interface Props {
  stats: ProcurementDashboardStats;
  onAction?: (actionType: string, entity: any) => void;
}

const DEFAULT_RFQS: RfqComparison[] = [
  {
    rfq_id: 'RFQ-2026-0090',
    pr_number: 'PR-2026-0043',
    item_description: 'High-Speed Office Printers (x 3 units)',
    category: 'IT Hardware',
    target_qty: 3,
    budget_myr: 18000.0,
    status: 'Open Sourcing',
    quotes: [],
  },
  {
    rfq_id: 'RFQ-2026-0089',
    pr_number: 'PR-2026-0042',
    item_description: 'Dell Latitude 5540 Laptops (x 10 units)',
    category: 'IT Hardware',
    target_qty: 10,
    budget_myr: 50000.0,
    status: 'Open Sourcing',
    quotes: [
      {
        vendor: 'NexTech Distribution Sdn Bhd',
        unit_price: 4800.0,
        total_amount: 48000.0,
        lead_time_days: 5,
        payment_terms: 'Net 30',
        sla_status: 'Top Tier (98%)',
        selected: true,
      },
      {
        vendor: 'Vortex Supplies Sdn Bhd',
        unit_price: 5100.0,
        total_amount: 51000.0,
        lead_time_days: 3,
        payment_terms: 'Net 14',
        sla_status: 'Under Review (78%)',
      },
      {
        vendor: 'Pacific Hardware Co',
        unit_price: 4950.0,
        total_amount: 49500.0,
        lead_time_days: 7,
        payment_terms: 'Net 30',
        sla_status: 'Satisfactory (85%)',
      },
    ],
  },
  {
    rfq_id: 'RFQ-2026-0088',
    pr_number: 'PR-2026-0041',
    item_description: 'Ergonomic Mesh Chairs Elite (x 15 units)',
    category: 'Furniture',
    target_qty: 15,
    budget_myr: 12000.0,
    status: 'Open Sourcing',
    quotes: [
      {
        vendor: 'Office Comfort Ltd',
        unit_price: 750.0,
        total_amount: 11250.0,
        lead_time_days: 10,
        payment_terms: 'Net 30',
        sla_status: 'Top Tier (95%)',
        selected: true,
      },
      {
        vendor: 'ErgoDesign Solutions',
        unit_price: 790.0,
        total_amount: 11850.0,
        lead_time_days: 4,
        payment_terms: 'Net 14',
        sla_status: 'Satisfactory (88%)',
      },
    ],
  },
];

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const BORDER = 'var(--samurai-border)';
const SURFACE_2 = 'var(--samurai-surface-2)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
function Th({ children, align, selected }: { children: React.ReactNode; align: 'left' | 'right' | 'center'; selected?: boolean }) {
  return <th className="px-4 py-3" style={{ ...th, textAlign: align, background: selected ? 'color-mix(in srgb, var(--samurai-ok) 10%, transparent)' : undefined, color: selected ? 'var(--samurai-ok)' : undefined, fontWeight: selected ? 700 : 500 }}>{children}</th>;
}

export function RfqVendorSourcingTab({ stats, onAction }: Props) {
  const rfqList = stats.rfqComparisons && stats.rfqComparisons.length > 0 ? stats.rfqComparisons : DEFAULT_RFQS;
  const [selectedRfqId, setSelectedRfqId] = useState<string>(rfqList[0]?.rfq_id ?? '');

  const activeRfq = rfqList.find((r) => r.rfq_id === selectedRfqId) || rfqList[0];

  return (
    <div className="sd-stack">
      {/* Normal Header Card */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">RFQ & Vendor Sourcing</h3>
        <p className="sd-chart-sub">
          Side-by-side vendor quotation comparison matrix for approved requisitions.
        </p>

        {/* RFQ Queue Selector Tabs */}
        <div className="sd-theme-seg" style={{ marginTop: '0.5rem', padding: '0.25rem', flexWrap: 'wrap', gap: '0.35rem' }}>
          {rfqList.map((rfq) => (
            <button
              key={rfq.rfq_id}
              type="button"
              onClick={() => setSelectedRfqId(rfq.rfq_id)}
              className={activeRfq?.rfq_id === rfq.rfq_id ? 'active' : ''}
              style={{ fontSize: '0.72rem', padding: '0.35rem 0.75rem', borderRadius: '0.4rem', whiteSpace: 'nowrap', width: 'auto' }}
            >
              {rfq.rfq_id} ({rfq.pr_number})
            </button>
          ))}
        </div>
      </div>

      {/* Active RFQ Detail Card */}
      {activeRfq && (
        <div className="sd-chart-card sd-stack">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between" style={{ borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.75rem' }}>
            <div>
              <div className="flex items-center gap-2">
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: TEXT }}>{activeRfq.rfq_id} — {activeRfq.item_description}</h4>
                <span className={`sd-chip ${activeRfq.quotes.length === 0 ? 'warn' : 'muted'}`}>{activeRfq.status}</span>
              </div>
              <p style={{ marginTop: '0.2rem', fontSize: '0.72rem', color: MUTED }}>
                Source PR: <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, color: TEXT }}>{activeRfq.pr_number}</span> · Target Qty: {activeRfq.target_qty} units · Category: {activeRfq.category}
              </p>
            </div>
            <div className="mt-2 sm:mt-0 text-right">
              <div style={{ fontSize: '0.72rem', color: MUTED }}>Target Budget</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.05rem', fontWeight: 700, color: TEXT }}>RM {activeRfq.budget_myr.toLocaleString()}</div>
            </div>
          </div>

          {/* If No Quotations Logged Yet */}
          {activeRfq.quotes.length === 0 ? (
            <div className="sd-empty" style={{ minHeight: '14rem' }}>
              <FileText className="h-10 w-10" style={{ color: MUTED }} />
              <h2>No Quotations Logged Yet</h2>
              <p style={{ maxWidth: '24rem' }}>
                Upload vendor quotation documents or PDF proposals to build the side-by-side comparison matrix for {activeRfq.rfq_id}.
              </p>
              <button
                type="button"
                onClick={() => onAction?.('upload_quotation', activeRfq)}
                className="sd-btn sd-btn-primary"
                style={{ marginTop: '0.5rem' }}
              >
                <Upload className="h-4 w-4" /> Upload Quotation
              </button>
            </div>
          ) : (
            /* Side-by-Side Comparison Matrix */
            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] text-sm" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <Th align="left">Quotation Criteria</Th>
                    {activeRfq.quotes.map((q) => (
                      <Th key={q.vendor} align="center" selected={q.selected}>
                        <div style={{ fontWeight: 600 }}>{q.vendor}</div>
                        {q.selected && <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.68rem', fontWeight: 700, color: 'var(--samurai-ok)' }}>✓ Selected Supplier</span>}
                      </Th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Unit Price Row */}
                  <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-4 py-3" style={{ fontWeight: 600, color: TEXT, width: '12rem' }}>Unit Price (MYR)</td>
                    {activeRfq.quotes.map((q) => {
                      const minPrice = Math.min(...activeRfq.quotes.map((x) => x.unit_price));
                      const isLowest = q.unit_price === minPrice;
                      return (
                        <td key={q.vendor} className="px-4 py-3 text-center" style={{ fontWeight: 600, color: TEXT }}>
                          RM {q.unit_price.toLocaleString()}
                          {isLowest && (
                            <span className="sd-chip ok" style={{ marginLeft: '0.4rem' }}>
                              <Award className="h-3 w-3" /> Best Price
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Total Quote Row */}
                  <tr style={{ borderBottom: `1px solid ${BORDER}`, background: SURFACE_2 }}>
                    <td className="px-4 py-3" style={{ fontWeight: 600, color: TEXT }}>Total Quote Amount</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center" style={{ fontWeight: 700, color: TEXT }}>
                        RM {q.total_amount.toLocaleString()}
                      </td>
                    ))}
                  </tr>

                  {/* Lead Time Row */}
                  <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-4 py-3" style={{ fontWeight: 600, color: TEXT }}>Delivery Lead Time</td>
                    {activeRfq.quotes.map((q) => {
                      const minTime = Math.min(...activeRfq.quotes.map((x) => x.lead_time_days));
                      const isFastest = q.lead_time_days === minTime;
                      return (
                        <td key={q.vendor} className="px-4 py-3 text-center" style={{ color: TEXT }}>
                          {q.lead_time_days} Business Days
                          {isFastest && (
                            <span className="sd-chip muted" style={{ marginLeft: '0.4rem' }}>
                              <Zap className="h-3 w-3" /> Fastest
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Payment Terms Row */}
                  <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-4 py-3" style={{ fontWeight: 600, color: TEXT }}>Payment Terms</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center" style={{ color: MUTED, fontFamily: 'var(--font-display)' }}>
                        {q.payment_terms}
                      </td>
                    ))}
                  </tr>

                  {/* SLA Score Row */}
                  <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-4 py-3" style={{ fontWeight: 600, color: TEXT }}>Vendor SLA Rating</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center">
                        <span className={`sd-chip ${q.sla_status.includes('Top Tier') ? 'ok' : 'muted'}`}>
                          <ShieldCheck className="h-3 w-3" /> {q.sla_status}
                        </span>
                      </td>
                    ))}
                  </tr>

                  {/* Selection Action Row */}
                  <tr style={{ borderTop: `1px solid ${BORDER}`, background: SURFACE_2 }}>
                    <td className="px-4 py-3" style={{ fontWeight: 600, color: TEXT }}>Action</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center">
                        {q.selected ? (
                          <span className="sd-chip ok">✓ Awarded & Issued</span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => onAction?.('select_quote_issue_po', { rfq: activeRfq, quote: q })}
                            className="sd-btn sd-btn-primary"
                            style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}
                          >
                            Select & Issue PO
                          </button>
                        )}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

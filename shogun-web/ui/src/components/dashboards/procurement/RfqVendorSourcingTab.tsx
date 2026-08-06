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

export function RfqVendorSourcingTab({ stats, onAction }: Props) {
  const rfqList = stats.rfqComparisons && stats.rfqComparisons.length > 0 ? stats.rfqComparisons : DEFAULT_RFQS;
  const [selectedRfqId, setSelectedRfqId] = useState<string>(rfqList[0]?.rfq_id ?? '');

  const activeRfq = rfqList.find((r) => r.rfq_id === selectedRfqId) || rfqList[0];

  return (
    <div className="space-y-4">
      {/* Normal Header Card */}
      <div className="card p-4">
        <h3 className="text-base font-semibold text-slate-800">RFQ & Vendor Sourcing</h3>
        <p className="text-xs text-slate-500">
          Side-by-side vendor quotation comparison matrix for approved requisitions.
        </p>

        {/* RFQ Queue Selector Tabs */}
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {rfqList.map((rfq) => (
            <button
              key={rfq.rfq_id}
              type="button"
              onClick={() => setSelectedRfqId(rfq.rfq_id)}
              className={`rounded-lg px-3 py-1.5 font-medium transition-all ${activeRfq?.rfq_id === rfq.rfq_id ? 'bg-brand text-white font-semibold shadow-sm' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              {rfq.rfq_id} ({rfq.pr_number})
            </button>
          ))}
        </div>
      </div>

      {/* Active RFQ Detail Card */}
      {activeRfq && (
        <div className="card p-4 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-surface-border pb-3">
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-slate-900">{activeRfq.rfq_id} — {activeRfq.item_description}</h4>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${activeRfq.quotes.length === 0 ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'}`}>
                  {activeRfq.status}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-slate-500">
                Source PR: <span className="font-mono font-semibold text-slate-700">{activeRfq.pr_number}</span> · Target Qty: {activeRfq.target_qty} units · Category: {activeRfq.category}
              </p>
            </div>
            <div className="mt-2 sm:mt-0 text-right">
              <div className="text-xs text-slate-400">Target Budget</div>
              <div className="text-base font-bold text-slate-900">RM {activeRfq.budget_myr.toLocaleString()}</div>
            </div>
          </div>

          {/* If No Quotations Logged Yet */}
          {activeRfq.quotes.length === 0 ? (
            <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center bg-slate-50/50 space-y-3">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <h5 className="text-sm font-bold text-slate-800">No Quotations Logged Yet</h5>
                <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                  Upload vendor quotation documents or PDF proposals to build the side-by-side comparison matrix for {activeRfq.rfq_id}.
                </p>
              </div>
              <div className="pt-2 flex justify-center">
                <button
                  type="button"
                  onClick={() => onAction?.('upload_quotation', activeRfq)}
                  className="inline-flex items-center gap-2 rounded-md bg-brand px-4 py-2 text-xs font-semibold text-white shadow-sm hover:opacity-90 transition-opacity"
                >
                  <Upload className="h-4 w-4" /> Upload Quotation
                </button>
              </div>
            </div>
          ) : (
            /* Side-by-Side Comparison Matrix */
            <div className="overflow-x-auto rounded-lg border border-surface-border bg-white shadow-sm">
              <table className="w-full min-w-[850px] text-sm">
                <thead>
                  <tr className="border-b border-surface-border bg-slate-50/80 text-xs font-semibold text-slate-500">
                    <th className="px-4 py-3 text-left font-medium w-48">Quotation Criteria</th>
                    {activeRfq.quotes.map((q) => (
                      <th key={q.vendor} className={`px-4 py-3 text-center font-medium ${q.selected ? 'bg-emerald-50 text-emerald-900 font-bold' : ''}`}>
                        <div className="font-semibold">{q.vendor}</div>
                        {q.selected && <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600">✓ Selected Supplier</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border text-xs">
                  {/* Unit Price Row */}
                  <tr className="hover:bg-slate-50/60">
                    <td className="px-4 py-3 font-semibold text-slate-700">Unit Price (MYR)</td>
                    {activeRfq.quotes.map((q) => {
                      const minPrice = Math.min(...activeRfq.quotes.map((x) => x.unit_price));
                      const isLowest = q.unit_price === minPrice;
                      return (
                        <td key={q.vendor} className="px-4 py-3 text-center font-semibold text-slate-900">
                          RM {q.unit_price.toLocaleString()}
                          {isLowest && (
                            <span className="ml-1.5 inline-flex items-center gap-1 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700">
                              <Award className="h-3 w-3" /> Best Price
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Total Quote Row */}
                  <tr className="hover:bg-slate-50/60 bg-slate-50/30">
                    <td className="px-4 py-3 font-semibold text-slate-700">Total Quote Amount</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center font-bold text-slate-900">
                        RM {q.total_amount.toLocaleString()}
                      </td>
                    ))}
                  </tr>

                  {/* Lead Time Row */}
                  <tr className="hover:bg-slate-50/60">
                    <td className="px-4 py-3 font-semibold text-slate-700">Delivery Lead Time</td>
                    {activeRfq.quotes.map((q) => {
                      const minTime = Math.min(...activeRfq.quotes.map((x) => x.lead_time_days));
                      const isFastest = q.lead_time_days === minTime;
                      return (
                        <td key={q.vendor} className="px-4 py-3 text-center text-slate-800">
                          {q.lead_time_days} Business Days
                          {isFastest && (
                            <span className="ml-1.5 inline-flex items-center gap-1 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-bold text-blue-700">
                              <Zap className="h-3 w-3" /> Fastest
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Payment Terms Row */}
                  <tr className="hover:bg-slate-50/60">
                    <td className="px-4 py-3 font-semibold text-slate-700">Payment Terms</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center text-slate-600 font-mono">
                        {q.payment_terms}
                      </td>
                    ))}
                  </tr>

                  {/* SLA Score Row */}
                  <tr className="hover:bg-slate-50/60">
                    <td className="px-4 py-3 font-semibold text-slate-700">Vendor SLA Rating</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${q.sla_status.includes('Top Tier') ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>
                          <ShieldCheck className="h-3 w-3" /> {q.sla_status}
                        </span>
                      </td>
                    ))}
                  </tr>

                  {/* Selection Action Row */}
                  <tr className="bg-slate-50/90 border-t border-slate-200">
                    <td className="px-4 py-3 font-semibold text-slate-800">Action</td>
                    {activeRfq.quotes.map((q) => (
                      <td key={q.vendor} className="px-4 py-3 text-center">
                        {q.selected ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                            ✓ Awarded & Issued
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => onAction?.('select_quote_issue_po', { rfq: activeRfq, quote: q })}
                            className="rounded-md bg-brand px-3 py-1 text-xs font-semibold text-white hover:opacity-90 transition-opacity shadow-sm"
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

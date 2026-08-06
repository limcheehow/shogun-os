import { useState } from "react";
import { ShieldCheck, AlertCircle, CheckCircle2 } from "lucide-react";
import type {
  ProcurementDashboardStats,
  ThreeWayMatchItem,
} from "../../../lib/types";

interface Props {
  stats: ProcurementDashboardStats;
  onAction?: (actionType: string, entity: any) => void;
}

const DEFAULT_MATCHES: ThreeWayMatchItem[] = [
  {
    match_id: "MATCH-2026-0101",
    po_number: "PO-2026-0218",
    grn_number: "GRN-2026-0091",
    invoice_number: "INV-NT-9842",
    vendor: "NexTech Distribution Sdn Bhd",
    po_amount: 52400.0,
    grn_received_amount: 52400.0,
    invoice_amount: 52400.0,
    variance_amount: 0.0,
    variance_pct: 0.0,
    match_status: "100% Match",
    ap_approval_status: "Pending AP Review",
  },
  {
    match_id: "MATCH-2026-0102",
    po_number: "PO-2026-0217",
    grn_number: "GRN-2026-0089",
    invoice_number: "INV-VT-4412",
    vendor: "Vortex Supplies Sdn Bhd",
    po_amount: 18750.0,
    grn_received_amount: 18750.0,
    invoice_amount: 18900.0,
    variance_amount: 150.0,
    variance_pct: 0.8,
    match_status: "Within Tolerance",
    ap_approval_status: "Pending AP Review",
  },
  {
    match_id: "MATCH-2026-0103",
    po_number: "PO-2026-0215",
    grn_number: "GRN-2026-0085",
    invoice_number: "INV-NT-9799",
    vendor: "NexTech Distribution Sdn Bhd",
    po_amount: 142000.0,
    grn_received_amount: 142000.0,
    invoice_amount: 148500.0,
    variance_amount: 6500.0,
    variance_pct: 4.5,
    match_status: "Variance Exceeded",
    ap_approval_status: "Flagged to Procurement",
  },
];

const MATCH_BADGE: Record<string, string> = {
  "100% Match": "bg-emerald-100 text-emerald-800 border-emerald-300",
  "Within Tolerance": "bg-amber-100 text-amber-800 border-amber-300",
  "Variance Exceeded": "bg-rose-100 text-rose-800 border-rose-300",
};

export function ThreeWayMatchTab({ stats, onAction }: Props) {
  const matchList =
    stats.threeWayMatches && stats.threeWayMatches.length > 0
      ? stats.threeWayMatches
      : DEFAULT_MATCHES;
  const [selectedMatchId, setSelectedMatchId] = useState<string>(
    matchList[0]?.match_id ?? "",
  );

  const activeMatch =
    matchList.find((m) => m.match_id === selectedMatchId) || matchList[0];

  return (
    <div className="space-y-4">
      {/* Normal Header Card */}
      <div className="card p-4">
        <h3 className="text-base font-semibold text-slate-800">
          Invoice Matching
        </h3>
        <p className="text-xs text-slate-500">
          Reconciliation log comparing PO benchmark, store receipt (GRN), and
          vendor invoice totals.
        </p>

        {/* Match Queue Dropdown Selector */}
        <div className="mt-3 flex flex-col sm:flex-row sm:items-center gap-2 text-xs">
          <label className="font-semibold text-slate-700 shrink-0">
            Select Verification Record:
          </label>
          <select
            value={selectedMatchId}
            onChange={(e) => setSelectedMatchId(e.target.value)}
            className="w-full sm:w-auto rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-mono text-xs font-semibold text-slate-800 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/30 shadow-sm"
          >
            {matchList.map((m) => (
              <option key={m.match_id} value={m.match_id}>
                {m.match_id} ({m.po_number})
              </option>
            ))}
          </select>
        </div>
      </div>

      {activeMatch && (
        <div className="card p-5 space-y-4">
          {/* Status Verdict Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-surface-border pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-bold text-slate-800">
                  {activeMatch.match_id}
                </span>
                <span className="text-xs font-medium text-slate-500">
                  {activeMatch.vendor}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-0.5 text-xs font-bold ${MATCH_BADGE[activeMatch.match_status]}`}
                >
                  {activeMatch.match_status === "100% Match" ? (
                    <ShieldCheck className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  {activeMatch.match_status} (
                  {activeMatch.variance_pct > 0
                    ? `+${activeMatch.variance_pct}% Variance`
                    : "0% Variance"}
                  )
                </span>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${activeMatch.ap_approval_status === "Approved for Payment" ? "bg-emerald-100 text-emerald-800" : activeMatch.ap_approval_status === "Flagged to Procurement" ? "bg-rose-100 text-rose-800" : "bg-amber-100 text-amber-800"}`}
                >
                  {activeMatch.ap_approval_status}
                </span>
              </div>
            </div>

            <div className="mt-3 sm:mt-0">
              <span
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold ${activeMatch.ap_approval_status === "Approved for Payment" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"}`}
              >
                <CheckCircle2 className="h-4 w-4" />{" "}
                {activeMatch.ap_approval_status}
              </span>
            </div>
          </div>

          {/* 3-Way Match Side-by-Side Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Card 1: Purchase Order */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                1. Purchase Order (PO)
              </div>
              <div className="font-mono text-sm font-bold text-slate-900">
                {activeMatch.po_number}
              </div>
              <div className="text-xs text-slate-600">
                Agreed Unit Prices & Quantities
              </div>
              <div className="border-t border-slate-200 pt-2 flex justify-between items-center text-xs">
                <span className="text-slate-500">Agreed Amount:</span>
                <span className="font-bold text-slate-900">
                  RM {activeMatch.po_amount.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Card 2: Goods Receipt (GRN) */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                2. Goods Receipt (GRN)
              </div>
              <div className="font-mono text-sm font-bold text-slate-900">
                {activeMatch.grn_number}
              </div>
              <div className="text-xs text-slate-600">
                Storekeeper Verified Receipt
              </div>
              <div className="border-t border-slate-200 pt-2 flex justify-between items-center text-xs">
                <span className="text-slate-500">Received Value:</span>
                <span className="font-bold text-slate-900">
                  RM {activeMatch.grn_received_amount.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Card 3: Vendor Invoice */}
            <div
              className={`rounded-xl border p-4 space-y-2 ${activeMatch.variance_amount > 0 ? "border-amber-300 bg-amber-50/40" : "border-slate-200 bg-slate-50/70"}`}
            >
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                3. Vendor Invoice
              </div>
              <div className="font-mono text-sm font-bold text-slate-900">
                {activeMatch.invoice_number}
              </div>
              <div className="text-xs text-slate-600">Billed Invoice Total</div>
              <div className="border-t border-slate-200 pt-2 flex justify-between items-center text-xs">
                <span className="text-slate-500">Invoiced Amount:</span>
                <span
                  className={`font-bold ${activeMatch.variance_amount > 0 ? "text-amber-800 font-extrabold" : "text-slate-900"}`}
                >
                  RM {activeMatch.invoice_amount.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Variance Breakdown Table */}
          <div className="overflow-x-auto rounded-lg border border-surface-border bg-white shadow-sm">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-surface-border bg-slate-50/80 font-semibold text-slate-500">
                  <th className="px-3 py-2.5">Reconciliation Field</th>
                  <th className="px-3 py-2.5 text-right">PO Benchmark</th>
                  <th className="px-3 py-2.5 text-right">GRN Store Receipt</th>
                  <th className="px-3 py-2.5 text-right">Vendor Invoice</th>
                  <th className="px-3 py-2.5 text-right pr-6">
                    Variance (MYR)
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                <tr className="hover:bg-slate-50/50">
                  <td className="px-3 py-2.5 font-semibold text-slate-800">
                    Total Billed vs Received Valuation
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono">
                    RM {activeMatch.po_amount.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono">
                    RM {activeMatch.grn_received_amount.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono font-bold">
                    RM {activeMatch.invoice_amount.toLocaleString()}
                  </td>
                  <td
                    className={`px-3 py-2.5 text-right font-mono pr-6 font-bold ${activeMatch.variance_amount > 0 ? "text-rose-600" : "text-emerald-600"}`}
                  >
                    {activeMatch.variance_amount > 0
                      ? `+RM ${activeMatch.variance_amount.toLocaleString()}`
                      : "RM 0.00"}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-2 pt-2">
            {activeMatch.ap_approval_status === "Approved for Payment" ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3.5 py-1 text-xs font-bold text-emerald-800">
                ✓ Approved for Payment & Synced to AP
              </span>
            ) : activeMatch.variance_amount > 0 ? (
              <button
                type="button"
                onClick={() => onAction?.("flag_variance", activeMatch)}
                className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 transition-colors shadow-sm"
              >
                Flag Price Variance
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onAction?.("approve_match_bill", activeMatch)}
                className="rounded-md bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors shadow-sm"
              >
                Approve & Convert to AP Bill
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

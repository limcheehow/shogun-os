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
  "100% Match": "ok",
  "Within Tolerance": "warn",
  "Variance Exceeded": "bad",
};

const AP_APPROVAL_BADGE: Record<string, string> = {
  "Pending AP Review": "warn",
  "Approved for Payment": "ok",
  "Flagged to Procurement": "bad",
};

const MUTED = "var(--samurai-muted)";
const TEXT = "var(--samurai-text)";
const BORDER = "var(--samurai-border)";
const SURFACE_2 = "var(--samurai-surface-2)";

const th = { fontSize: "0.72rem", fontWeight: 500, color: MUTED } as const;

function Th({ children, align }: { children: React.ReactNode; align: "left" | "right" | "center" }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

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
    <div className="sd-stack">
      {/* Normal Header Card */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Invoice Matching</h3>
        <p className="sd-chart-sub">
          Reconciliation log comparing PO benchmark, store receipt (GRN), and
          vendor invoice totals.
        </p>

        {/* Match Queue Dropdown Selector */}
        <div style={{ marginTop: "0.75rem", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.5rem", fontSize: "0.72rem" }}>
          <label style={{ fontWeight: 600, color: TEXT, flexShrink: 0 }}>
            Select Verification Record:
          </label>
          <select
            value={selectedMatchId}
            onChange={(e) => setSelectedMatchId(e.target.value)}
            style={{ borderRadius: "0.5rem", border: `1px solid ${BORDER}`, background: "var(--samurai-surface)", color: TEXT, padding: "0.375rem 0.5rem", fontFamily: "var(--font-display)", fontSize: "0.72rem", fontWeight: 600 }}
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
        <div className="sd-chart-card sd-stack" style={{ gap: "1rem" }}>
          {/* Status Verdict Header */}
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${BORDER}`, paddingBottom: "0.75rem", gap: "0.5rem" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontFamily: "var(--font-display)", fontSize: "0.85rem", fontWeight: 700, color: TEXT }}>
                  {activeMatch.match_id}
                </span>
                <span style={{ fontSize: "0.72rem", color: MUTED }}>
                  {activeMatch.vendor}
                </span>
              </div>
              <div style={{ marginTop: "0.25rem", display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                <span className={`sd-chip ${MATCH_BADGE[activeMatch.match_status] ?? "muted"}`}>
                  {activeMatch.match_status === "100% Match" ? (
                    <ShieldCheck className="h-3.5 w-3.5" />
                  ) : (
                    <AlertCircle className="h-3.5 w-3.5" />
                  )}
                  {activeMatch.match_status} (
                  {activeMatch.variance_pct > 0
                    ? `+${activeMatch.variance_pct}% Variance`
                    : "0% Variance"}
                  )
                </span>
                <span className={`sd-chip ${AP_APPROVAL_BADGE[activeMatch.ap_approval_status] ?? "muted"}`}>
                  {activeMatch.ap_approval_status}
                </span>
              </div>
            </div>

            <div>
              <span className={`sd-chip ${activeMatch.ap_approval_status === "Approved for Payment" ? "ok" : "muted"}`}>
                <CheckCircle2 className="h-3.5 w-3.5" />{" "}
                {activeMatch.ap_approval_status}
              </span>
            </div>
          </div>

          {/* 3-Way Match Side-by-Side Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(16rem, 1fr))", gap: "1rem" }}>
            {/* Card 1: Purchase Order */}
            <div className="sd-card sd-stack" style={{ gap: "0.5rem" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, color: MUTED, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                1. Purchase Order (PO)
              </div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "0.85rem", fontWeight: 700, color: TEXT }}>
                {activeMatch.po_number}
              </div>
              <div style={{ fontSize: "0.72rem", color: MUTED }}>
                Agreed Unit Prices & Quantities
              </div>
              <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: "0.5rem", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.72rem" }}>
                <span style={{ color: MUTED }}>Agreed Amount:</span>
                <span style={{ fontWeight: 700, color: TEXT }}>
                  RM {activeMatch.po_amount.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Card 2: Goods Receipt (GRN) */}
            <div className="sd-card sd-stack" style={{ gap: "0.5rem" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, color: MUTED, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                2. Goods Receipt (GRN)
              </div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "0.85rem", fontWeight: 700, color: TEXT }}>
                {activeMatch.grn_number}
              </div>
              <div style={{ fontSize: "0.72rem", color: MUTED }}>
                Storekeeper Verified Receipt
              </div>
              <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: "0.5rem", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.72rem" }}>
                <span style={{ color: MUTED }}>Received Value:</span>
                <span style={{ fontWeight: 700, color: TEXT }}>
                  RM {activeMatch.grn_received_amount.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Card 3: Vendor Invoice */}
            <div
              className="sd-card sd-stack"
              style={{ gap: "0.5rem", borderColor: activeMatch.variance_amount > 0 ? "color-mix(in srgb, var(--samurai-warning) 45%, transparent)" : undefined, background: activeMatch.variance_amount > 0 ? "color-mix(in srgb, var(--samurai-warning) 8%, var(--samurai-surface))" : undefined }}
            >
              <div style={{ fontSize: "0.72rem", fontWeight: 700, color: MUTED, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                3. Vendor Invoice
              </div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "0.85rem", fontWeight: 700, color: TEXT }}>
                {activeMatch.invoice_number}
              </div>
              <div style={{ fontSize: "0.72rem", color: MUTED }}>Billed Invoice Total</div>
              <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: "0.5rem", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.72rem" }}>
                <span style={{ color: MUTED }}>Invoiced Amount:</span>
                <span style={{ fontWeight: 700, color: activeMatch.variance_amount > 0 ? "var(--samurai-warning)" : TEXT }}>
                  RM {activeMatch.invoice_amount.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Variance Breakdown Table */}
          <div className="overflow-x-auto">
            <table className="w-full" style={{ borderCollapse: "collapse", fontSize: "0.75rem" }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Reconciliation Field</Th>
                  <Th align="right">PO Benchmark</Th>
                  <Th align="right">GRN Store Receipt</Th>
                  <Th align="right">Vendor Invoice</Th>
                  <Th align="right">Variance (MYR)</Th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <td className="px-3 py-2.5" style={{ fontWeight: 600, color: TEXT }}>
                    Total Billed vs Received Valuation
                  </td>
                  <td className="px-3 py-2.5 text-right" style={{ fontFamily: "var(--font-display)", color: TEXT }}>
                    RM {activeMatch.po_amount.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 text-right" style={{ fontFamily: "var(--font-display)", color: TEXT }}>
                    RM {activeMatch.grn_received_amount.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 text-right" style={{ fontFamily: "var(--font-display)", fontWeight: 700, color: TEXT }}>
                    RM {activeMatch.invoice_amount.toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 text-right" style={{ fontFamily: "var(--font-display)", fontWeight: 700, color: activeMatch.variance_amount > 0 ? "var(--samurai-danger)" : "var(--samurai-ok)" }}>
                    {activeMatch.variance_amount > 0
                      ? `+RM ${activeMatch.variance_amount.toLocaleString()}`
                      : "RM 0.00"}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", paddingTop: "0.5rem" }}>
            {activeMatch.ap_approval_status === "Approved for Payment" ? (
              <span className="sd-chip ok">✓ Approved for Payment & Synced to AP</span>
            ) : activeMatch.variance_amount > 0 ? (
              <button
                type="button"
                onClick={() => onAction?.("flag_variance", activeMatch)}
                className="sd-btn sd-btn-secondary"
                style={{ color: "var(--samurai-warning)" }}
              >
                Flag Price Variance
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onAction?.("approve_match_bill", activeMatch)}
                className="sd-btn sd-btn-primary"
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

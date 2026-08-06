import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { PieChart } from "../charts";
import { chartColors } from "../../../lib/palette";
import type {
  ExecutiveApprovalRow,
  ProcurementDashboardStats,
  PurchaseOrderRow,
} from "../../../lib/types";

interface Props {
  stats: ProcurementDashboardStats;
  color: string;
  onAction?: (actionType: string, entity: unknown) => void;
}

const fmtMyr = (n: number) =>
  n >= 1_000_000
    ? `RM ${(n / 1_000_000).toFixed(2)}M`
    : `RM ${(n / 1_000).toFixed(0)}K`;

const FULFILLMENT_STYLE: Record<string, string> = {
  Draft: "muted",
  "Pending Approval": "warn",
  "Issued to Vendor": "muted",
  "Partially Received": "muted",
  "Fully Received & Billed": "ok",
};

const APPROVAL_STYLE: Record<string, string> = {
  Draft: "muted",
  "Pending Approval": "warn",
  Approved: "ok",
  Issued: "muted",
  Cancelled: "bad",
};

const SLA_STYLE: Record<string, string> = {
  "Top Tier": "ok",
  Satisfactory: "muted",
  "Under Review": "warn",
};

const APPROVAL_QUEUE_STYLE: Record<string, string> = {
  "Pending Executive Approval": "warn",
  Approved: "ok",
  "Clarification Requested": "muted",
  Rejected: "bad",
};

const MUTED = "var(--samurai-muted)";
const TEXT = "var(--samurai-text)";
const BORDER = "var(--samurai-border)";
const SURFACE_2 = "var(--samurai-surface-2)";

const th = { fontSize: "0.72rem", fontWeight: 500, color: MUTED } as const;

function Th({
  children,
  align,
}: {
  children: React.ReactNode;
  align: "left" | "right" | "center";
}) {
  return (
    <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>
      {children}
    </th>
  );
}

// PO pipeline funnel stages use a token-based gradient (muted → warning → blue → indigo → ok).
const PIPELINE_COLORS = [
  "var(--samurai-muted)",
  "var(--samurai-warning)",
  "var(--samurai-blue)",
  "#6366f1",
  "var(--samurai-ok)",
];

export function PurchaseOrdersVendorTab({ stats, color, onAction }: Props) {
  const [statusFilter, setStatusFilter] = useState<string>(
    "Pending Executive Approval",
  );
  const [activePoApprovalFilter, setActivePoApprovalFilter] =
    useState<string>("All");
  const [poActionTarget, setPoActionTarget] = useState<PurchaseOrderRow | null>(
    null,
  );
  const [execActionTarget, setExecActionTarget] =
    useState<ExecutiveApprovalRow | null>(null);

  const approvalQueue = stats.executiveApprovalQueue ?? [];
  const filteredQueue = approvalQueue.filter((item) => {
    if (statusFilter === "All") return true;
    return item.approval_status === statusFilter;
  });

  const countPending = approvalQueue.filter(
    (i) => i.approval_status === "Pending Executive Approval",
  ).length;
  const countClarification = approvalQueue.filter(
    (i) => i.approval_status === "Clarification Requested",
  ).length;

  const activePos = stats.activePurchaseOrders ?? [];
  const filteredActivePos = activePos.filter((po) => {
    if (activePoApprovalFilter === "All") return true;
    return po.approval_status === activePoApprovalFilter;
  });

  const countActiveAll = activePos.length;
  const countActiveDraft = activePos.filter(
    (p) => p.approval_status === "Draft",
  ).length;
  const countActiveApproved = activePos.filter(
    (p) => p.approval_status === "Approved",
  ).length;
  const countActiveIssued = activePos.filter(
    (p) => p.approval_status === "Issued",
  ).length;
  const countActivePending = activePos.filter(
    (p) => p.approval_status === "Pending Approval",
  ).length;
  const countActiveCancelled = activePos.filter(
    (p) => p.approval_status === "Cancelled",
  ).length;

  const concentrationAlert = stats.vendorSpendConcentration.find(
    (v) => v.spend_pct > 25,
  );

  return (
    <div className="sd-stack">
      {/* PO Pipeline Card (Funnel) */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">PO Lifecycle Pipeline (Funnel)</h3>
        {stats.poPipeline.length === 0 ? (
          <p style={{ color: MUTED, fontSize: "0.85rem" }}>
            No PO pipeline stages available yet.
          </p>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                height: "2rem",
                borderRadius: "0.5rem",
                overflow: "hidden",
                background: SURFACE_2,
                marginBottom: "0.5rem",
              }}
            >
              {stats.poPipeline.map((stage, i) => {
                const totalCount = stats.poPipeline.reduce(
                  (sum, s) => sum + s.count,
                  0,
                );
                const widthPct =
                  totalCount > 0 ? (stage.count / totalCount) * 100 : 0;
                return (
                  <div
                    key={stage.stage}
                    style={{
                      width: `${widthPct}%`,
                      background: PIPELINE_COLORS[i % PIPELINE_COLORS.length],
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.72rem",
                      fontWeight: 600,
                      color: "#fff",
                    }}
                    title={`${stage.stage}: ${stage.count} POs (${fmtMyr(stage.value)})`}
                  >
                    <span>{stage.count}</span>
                  </div>
                );
              })}
            </div>
            <div
              style={{
                display: "flex",
                overflowX: "auto",
                paddingBottom: "0.25rem",
                fontSize: "0.72rem",
              }}
            >
              {stats.poPipeline.map((stage, i) => {
                const totalCount = stats.poPipeline.reduce(
                  (sum, s) => sum + s.count,
                  0,
                );
                const widthPct =
                  totalCount > 0 ? (stage.count / totalCount) * 100 : 0;
                return (
                  <div
                    key={stage.stage}
                    style={{
                      width: `${widthPct}%`,
                      minWidth: "5rem",
                      padding: "0 0.25rem",
                      textAlign: "center",
                      flexShrink: 0,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "0.375rem",
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          height: "0.625rem",
                          width: "0.625rem",
                          borderRadius: "0.125rem",
                          background:
                            PIPELINE_COLORS[i % PIPELINE_COLORS.length],
                        }}
                      />
                      <span style={{ fontWeight: 600, color: TEXT }}>
                        {stage.stage}
                      </span>
                    </div>
                    <div style={{ color: MUTED }}>{fmtMyr(stage.value)}</div>
                  </div>
                );
              })}
            </div>
            <p
              style={{ marginTop: "0.5rem", fontSize: "0.72rem", color: MUTED }}
            >
              Pipeline flow: Draft → Pending Approval → Issued to Vendor →
              Partially Received → Fully Received & Billed
            </p>
          </>
        )}
      </div>

      {/* Executive PO Approval Queue (> MYR 10,000) */}
      <div className="sd-chart-card">
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.5rem",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "0.5rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <h3 className="sd-chart-title" style={{ margin: 0 }}>
              Executive PO Approval Queue (&gt; MYR 10,000)
            </h3>
            <span className="sd-chip warn">CEO / CFO / CPO sign-off</span>
          </div>
          <div
            className="sd-theme-seg"
            style={{ flexWrap: "wrap", gap: "0.35rem" }}
          >
            <button
              type="button"
              onClick={() => setStatusFilter("Pending Executive Approval")}
              className={
                statusFilter === "Pending Executive Approval" ? "active" : ""
              }
              style={{
                fontSize: "0.72rem",
                padding: "0.35rem 0.7rem",
                borderRadius: "0.4rem",
                whiteSpace: "nowrap",
                width: "auto",
              }}
            >
              Pending Approval ({countPending})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("Clarification Requested")}
              className={
                statusFilter === "Clarification Requested" ? "active" : ""
              }
              style={{
                fontSize: "0.72rem",
                padding: "0.35rem 0.7rem",
                borderRadius: "0.4rem",
                whiteSpace: "nowrap",
                width: "auto",
              }}
            >
              Clarification Requested ({countClarification})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("All")}
              className={statusFilter === "All" ? "active" : ""}
              style={{
                fontSize: "0.72rem",
                padding: "0.35rem 0.7rem",
                borderRadius: "0.4rem",
                whiteSpace: "nowrap",
                width: "auto",
              }}
            >
              All ({approvalQueue.length})
            </button>
          </div>
        </div>
        <p className="sd-chart-sub" style={{ marginBottom: "0.75rem" }}>
          Requisitions above the MYR 10,000 executive approval threshold.
          Requires sign-off before vendor issue.
        </p>
        {filteredQueue.length === 0 ? (
          <p
            style={{
              padding: "1rem 0",
              textAlign: "center",
              fontSize: "0.85rem",
              color: MUTED,
            }}
          >
            No POs matching status &ldquo;{statusFilter}&rdquo;.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table
              className="w-full text-sm"
              style={{ borderCollapse: "collapse" }}
            >
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">PO Number</Th>
                  <Th align="left">Vendor</Th>
                  <Th align="left">Order Date</Th>
                  <Th align="right">Total Amount</Th>
                  <Th align="left">Requester / Dept</Th>
                  <Th align="right">Threshold</Th>
                  <Th align="center">Status</Th>
                  <Th align="center">Action</Th>
                </tr>
              </thead>
              <tbody>
                {filteredQueue.map((po) => (
                  <tr
                    key={po.po_number}
                    style={{ borderBottom: `1px solid ${BORDER}` }}
                  >
                    <td
                      className="px-3 py-2.5"
                      style={{
                        fontFamily: "var(--font-display)",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: TEXT,
                      }}
                    >
                      {po.po_number}
                    </td>
                    <td
                      className="px-3 py-2.5"
                      style={{ fontWeight: 600, color: TEXT }}
                    >
                      {po.vendor}
                    </td>
                    <td className="px-3 py-2.5" style={{ color: MUTED }}>
                      {po.order_date}
                    </td>
                    <td
                      className="px-3 py-2.5 text-right"
                      style={{ fontWeight: 600, color: TEXT }}
                    >
                      RM{" "}
                      {po.total_amount.toLocaleString("en-MY", {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-3 py-2.5" style={{ color: MUTED }}>
                      {po.requester_dept}
                    </td>
                    <td
                      className="px-3 py-2.5 text-right"
                      style={{ color: MUTED }}
                    >
                      RM {po.threshold_myr.toLocaleString()}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span
                        className={`sd-chip ${APPROVAL_QUEUE_STYLE[po.approval_status] ?? "muted"}`}
                      >
                        {po.approval_status}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <button
                        type="button"
                        onClick={() => setExecActionTarget(po)}
                        className="sd-btn sd-btn-secondary"
                        style={{
                          padding: "0.3rem 0.6rem",
                          fontSize: "0.72rem",
                        }}
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
          <button
            type="button"
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 40,
              background: "rgba(0,0,0,0.4)",
              border: "none",
              cursor: "default",
            }}
            onClick={() => setExecActionTarget(null)}
            aria-label="Close"
          />
          <div
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 50,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "1rem",
            }}
            onClick={() => setExecActionTarget(null)}
          >
            <div
              className="sd-card"
              style={{
                position: "relative",
                zIndex: 50,
                width: "100%",
                maxWidth: "26rem",
                height: "fit-content",
                padding: "1.25rem",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: `1px solid ${BORDER}`,
                  paddingBottom: "0.75rem",
                  marginBottom: "0.75rem",
                }}
              >
                <div>
                  <h2
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: "1rem",
                      fontWeight: 600,
                      color: TEXT,
                      margin: 0,
                    }}
                  >
                    Executive PO Approval Action
                  </h2>
                  <p style={{ fontSize: "0.72rem", color: MUTED, margin: 0 }}>
                    {execActionTarget.vendor} · {execActionTarget.po_number}
                  </p>
                </div>
                <button
                  type="button"
                  className="sd-icon-btn"
                  onClick={() => setExecActionTarget(null)}
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "0.5rem",
                  marginBottom: "0.75rem",
                }}
              >
                <div
                  style={{
                    borderRadius: "0.5rem",
                    background: SURFACE_2,
                    padding: "0.6rem",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "0.72rem", color: MUTED }}>
                    PO Total Amount
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 600,
                      color: TEXT,
                    }}
                  >
                    RM{" "}
                    {execActionTarget.total_amount.toLocaleString("en-MY", {
                      minimumFractionDigits: 2,
                    })}
                  </div>
                </div>
                <div
                  style={{
                    borderRadius: "0.5rem",
                    background: SURFACE_2,
                    padding: "0.6rem",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "0.72rem", color: MUTED }}>
                    Requester Dept
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 600,
                      color: "var(--samurai-lime)",
                    }}
                  >
                    {execActionTarget.requester_dept}
                  </div>
                </div>
              </div>

              <div
                style={{
                  borderTop: `1px solid ${BORDER}`,
                  paddingTop: "0.75rem",
                }}
              >
                <p
                  style={{
                    fontSize: "0.72rem",
                    color: MUTED,
                    marginBottom: "0.6rem",
                  }}
                >
                  Select action to send to Chotatsu (Procurement Agent):
                </p>
                <div className="sd-stack" style={{ gap: "0.4rem" }}>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.("approve_po", execActionTarget);
                      setExecActionTarget(null);
                    }}
                    className="sd-btn sd-btn-primary"
                    style={{ justifyContent: "space-between" }}
                  >
                    <span>Approve PO</span>
                    <span style={{ fontSize: "0.72rem", fontWeight: 700 }}>
                      →
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.("reject_po", execActionTarget);
                      setExecActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{
                      justifyContent: "space-between",
                      color: "var(--samurai-danger)",
                    }}
                  >
                    <span>Reject PO</span>
                    <span style={{ fontSize: "0.72rem" }}>→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.("request_clarification", execActionTarget);
                      setExecActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{ justifyContent: "space-between" }}
                  >
                    <span>Request Clarification</span>
                    <span style={{ fontSize: "0.72rem" }}>→</span>
                  </button>
                  {execActionTarget.approval_status ===
                    "Clarification Requested" && (
                    <button
                      type="button"
                      onClick={() => {
                        onAction?.("reply_clarification", execActionTarget);
                        setExecActionTarget(null);
                      }}
                      className="sd-btn sd-btn-secondary"
                      style={{ justifyContent: "space-between" }}
                    >
                      <span>Reply Clarification & Resubmit</span>
                      <span style={{ fontSize: "0.72rem" }}>→</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Active Purchase Orders Queue Table */}
      <div className="sd-chart-card">
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.5rem",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "0.75rem",
          }}
        >
          <h3 className="sd-chart-title" style={{ margin: 0 }}>
            Active Purchase Orders
          </h3>
          <div
            className="sd-theme-seg"
            style={{ flexWrap: "wrap", gap: "0.35rem" }}
          >
            <button
              type="button"
              onClick={() => setActivePoApprovalFilter("All")}
              className={activePoApprovalFilter === "All" ? "active" : ""}
              style={{
                fontSize: "0.72rem",
                padding: "0.35rem 0.7rem",
                borderRadius: "0.4rem",
                whiteSpace: "nowrap",
                width: "auto",
              }}
            >
              All ({countActiveAll})
            </button>
            <button
              type="button"
              onClick={() => setActivePoApprovalFilter("Draft")}
              className={activePoApprovalFilter === "Draft" ? "active" : ""}
              style={{
                fontSize: "0.72rem",
                padding: "0.35rem 0.7rem",
                borderRadius: "0.4rem",
                whiteSpace: "nowrap",
                width: "auto",
              }}
            >
              Draft ({countActiveDraft})
            </button>
            {countActiveApproved > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter("Approved")}
                className={
                  activePoApprovalFilter === "Approved" ? "active" : ""
                }
                style={{
                  fontSize: "0.72rem",
                  padding: "0.35rem 0.7rem",
                  borderRadius: "0.4rem",
                  whiteSpace: "nowrap",
                  width: "auto",
                }}
              >
                Approved ({countActiveApproved})
              </button>
            )}
            {countActiveIssued > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter("Issued")}
                className={activePoApprovalFilter === "Issued" ? "active" : ""}
                style={{
                  fontSize: "0.72rem",
                  padding: "0.35rem 0.7rem",
                  borderRadius: "0.4rem",
                  whiteSpace: "nowrap",
                  width: "auto",
                }}
              >
                Issued ({countActiveIssued})
              </button>
            )}
            {countActivePending > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter("Pending Approval")}
                className={
                  activePoApprovalFilter === "Pending Approval" ? "active" : ""
                }
                style={{
                  fontSize: "0.72rem",
                  padding: "0.35rem 0.7rem",
                  borderRadius: "0.4rem",
                  whiteSpace: "nowrap",
                  width: "auto",
                }}
              >
                Pending ({countActivePending})
              </button>
            )}
            {countActiveCancelled > 0 && (
              <button
                type="button"
                onClick={() => setActivePoApprovalFilter("Cancelled")}
                className={
                  activePoApprovalFilter === "Cancelled" ? "active" : ""
                }
                style={{
                  fontSize: "0.72rem",
                  padding: "0.35rem 0.7rem",
                  borderRadius: "0.4rem",
                  whiteSpace: "nowrap",
                  width: "auto",
                }}
              >
                Cancelled ({countActiveCancelled})
              </button>
            )}
          </div>
        </div>
        {filteredActivePos.length === 0 ? (
          <p
            style={{
              padding: "1rem 0",
              textAlign: "center",
              fontSize: "0.85rem",
              color: MUTED,
            }}
          >
            No active POs matching approval state &ldquo;
            {activePoApprovalFilter}&rdquo;.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table
              className="w-full text-sm"
              style={{ borderCollapse: "collapse" }}
            >
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">PO Number</Th>
                  <Th align="left">Vendor</Th>
                  <Th align="left">Order Date</Th>
                  <Th align="left">Expected Delivery</Th>
                  <Th align="right">Total Amount</Th>
                  <Th align="center">Fulfillment</Th>
                  <Th align="center">Approval</Th>
                  <Th align="center">Action</Th>
                </tr>
              </thead>
              <tbody>
                {filteredActivePos.map((po) => {
                  const overdue =
                    new Date(po.expected_delivery) < new Date() &&
                    po.fulfillment_status !== "Fully Received & Billed";
                  return (
                    <tr
                      key={po.po_number}
                      style={{ borderBottom: `1px solid ${BORDER}` }}
                    >
                      <td
                        className="px-3 py-2.5"
                        style={{
                          fontFamily: "var(--font-display)",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          color: TEXT,
                        }}
                      >
                        {po.po_number}
                      </td>
                      <td
                        className="px-3 py-2.5"
                        style={{ fontWeight: 600, color: TEXT }}
                      >
                        {po.vendor}
                      </td>
                      <td className="px-3 py-2.5" style={{ color: MUTED }}>
                        {po.order_date}
                      </td>
                      <td
                        className="px-3 py-2.5"
                        style={{
                          color: overdue ? "var(--samurai-danger)" : MUTED,
                          fontWeight: overdue ? 600 : 400,
                        }}
                      >
                        {po.expected_delivery}
                        {overdue ? " ⚠" : ""}
                      </td>
                      <td
                        className="px-3 py-2.5 text-right"
                        style={{ fontWeight: 600, color: TEXT }}
                      >
                        RM{" "}
                        {po.total_amount.toLocaleString("en-MY", {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span
                          className={`sd-chip ${FULFILLMENT_STYLE[po.fulfillment_status] ?? "muted"}`}
                        >
                          {po.fulfillment_status}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span
                          className={`sd-chip ${APPROVAL_STYLE[po.approval_status] ?? "muted"}`}
                        >
                          {po.approval_status}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <button
                          type="button"
                          onClick={() => setPoActionTarget(po)}
                          className="sd-btn sd-btn-secondary"
                          style={{
                            padding: "0.3rem 0.6rem",
                            fontSize: "0.72rem",
                          }}
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
          <button
            type="button"
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 40,
              background: "rgba(0,0,0,0.4)",
              border: "none",
              cursor: "default",
            }}
            onClick={() => setPoActionTarget(null)}
            aria-label="Close"
          />
          <div
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 50,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "1rem",
            }}
            onClick={() => setPoActionTarget(null)}
          >
            <div
              className="sd-card"
              style={{
                position: "relative",
                zIndex: 50,
                width: "100%",
                maxWidth: "26rem",
                height: "fit-content",
                padding: "1.25rem",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: `1px solid ${BORDER}`,
                  paddingBottom: "0.75rem",
                  marginBottom: "0.75rem",
                }}
              >
                <div>
                  <h2
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: "1rem",
                      fontWeight: 600,
                      color: TEXT,
                      margin: 0,
                    }}
                  >
                    PO Action
                  </h2>
                  <p style={{ fontSize: "0.72rem", color: MUTED, margin: 0 }}>
                    {poActionTarget.vendor} · {poActionTarget.po_number}
                  </p>
                </div>
                <button
                  type="button"
                  className="sd-icon-btn"
                  onClick={() => setPoActionTarget(null)}
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "0.5rem",
                  marginBottom: "0.75rem",
                }}
              >
                <div
                  style={{
                    borderRadius: "0.5rem",
                    background: SURFACE_2,
                    padding: "0.6rem",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "0.72rem", color: MUTED }}>
                    PO Total Amount
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 600,
                      color: TEXT,
                    }}
                  >
                    RM{" "}
                    {poActionTarget.total_amount.toLocaleString("en-MY", {
                      minimumFractionDigits: 2,
                    })}
                  </div>
                </div>
                <div
                  style={{
                    borderRadius: "0.5rem",
                    background: SURFACE_2,
                    padding: "0.6rem",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "0.72rem", color: MUTED }}>
                    Expected Delivery
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 600,
                      color: "var(--samurai-lime)",
                    }}
                  >
                    {poActionTarget.expected_delivery}
                  </div>
                </div>
              </div>

              <div
                style={{
                  borderTop: `1px solid ${BORDER}`,
                  paddingTop: "0.75rem",
                }}
              >
                <p
                  style={{
                    fontSize: "0.72rem",
                    color: MUTED,
                    marginBottom: "0.6rem",
                  }}
                >
                  Select action to send to Chotatsu (Procurement Agent):
                </p>
                <div className="sd-stack" style={{ gap: "0.4rem" }}>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.("receive_grn", poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{ justifyContent: "space-between" }}
                  >
                    <span>Receive Goods (GRN)</span>
                    <span style={{ fontSize: "0.72rem" }}>→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.("sync_bill", poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{ justifyContent: "space-between" }}
                  >
                    <span>Sync Bill to Accounting</span>
                    <span style={{ fontSize: "0.72rem" }}>→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.("send_reminder", poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{ justifyContent: "space-between" }}
                  >
                    <span>Send Delivery Reminder to Vendor</span>
                    <span style={{ fontSize: "0.72rem" }}>→</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onAction?.("cancel_po", poActionTarget);
                      setPoActionTarget(null);
                    }}
                    className="sd-btn sd-btn-secondary"
                    style={{
                      justifyContent: "space-between",
                      color: "var(--samurai-danger)",
                    }}
                  >
                    <span>Cancel Purchase Order</span>
                    <span style={{ fontSize: "0.72rem" }}>→</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Vendor Scorecard & Spend Concentration */}
      <div className="sd-row">
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Vendor Scorecard & SLA Ratings</h3>
          {stats.vendorScorecard.length === 0 ? (
            <p style={{ color: MUTED, fontSize: "0.85rem" }}>
              No vendor scorecard data available yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table
                className="w-full text-sm"
                style={{ borderCollapse: "collapse" }}
              >
                <thead>
                  <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <Th align="left">Vendor Name</Th>
                    <Th align="right">YTD Spend</Th>
                    <Th align="right">On-Time</Th>
                    <Th align="right">Quality</Th>
                    <Th align="center">SLA Rating</Th>
                  </tr>
                </thead>
                <tbody>
                  {stats.vendorScorecard.map((v) => (
                    <tr
                      key={v.vendor}
                      style={{ borderBottom: `1px solid ${BORDER}` }}
                    >
                      <td
                        className="py-2"
                        style={{ fontWeight: 600, color: TEXT }}
                      >
                        {v.vendor}
                      </td>
                      <td
                        className="py-2 text-right"
                        style={{ fontWeight: 600, color: TEXT }}
                      >
                        RM{" "}
                        {v.ytd_spend.toLocaleString("en-MY", {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td
                        className="py-2 text-right"
                        style={{
                          fontWeight: 600,
                          color:
                            v.on_time_delivery_rate >= 90
                              ? "var(--samurai-ok)"
                              : v.on_time_delivery_rate >= 75
                                ? "var(--samurai-warning)"
                                : "var(--samurai-danger)",
                        }}
                      >
                        {v.on_time_delivery_rate.toFixed(0)}%
                      </td>
                      <td
                        className="py-2 text-right"
                        style={{
                          fontWeight: 600,
                          color:
                            v.quality_acceptance_rate >= 95
                              ? "var(--samurai-ok)"
                              : v.quality_acceptance_rate >= 85
                                ? "var(--samurai-warning)"
                                : "var(--samurai-danger)",
                        }}
                      >
                        {v.quality_acceptance_rate.toFixed(0)}%
                      </td>
                      <td className="py-2 text-center">
                        <span
                          className={`sd-chip ${SLA_STYLE[v.sla_status] ?? "muted"}`}
                        >
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
        <div className="sd-chart-card">
          <h3 className="sd-chart-title">Vendor Spend Concentration</h3>
          {concentrationAlert && (
            <div
              className="sd-alert-row critical"
              style={{ marginBottom: "0.75rem" }}
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>
                {concentrationAlert.vendor} represents{" "}
                {concentrationAlert.spend_pct.toFixed(1)}% of spend — supplier
                dependency risk (&gt;25%)
              </span>
            </div>
          )}
          {stats.vendorSpendConcentration.length === 0 ? (
            <p style={{ color: MUTED, fontSize: "0.85rem" }}>
              No vendor spend data available yet.
            </p>
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
              <div
                style={{
                  marginTop: "0.75rem",
                  borderTop: `1px solid ${BORDER}`,
                  paddingTop: "0.5rem",
                }}
              >
                {[...stats.vendorSpendConcentration]
                  .sort((a, b) => (b.spend ?? 0) - (a.spend ?? 0))
                  .map((v, i) => {
                    const colors = chartColors(
                      color,
                      stats.vendorSpendConcentration.length,
                    );
                    return (
                      <div
                        key={v.vendor}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "0.375rem 0",
                          fontSize: "0.75rem",
                          borderBottom: `1px solid ${BORDER}`,
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem",
                            minWidth: 0,
                            flex: 1,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          <span
                            style={{
                              display: "inline-block",
                              height: "0.625rem",
                              width: "0.625rem",
                              borderRadius: "999px",
                              flexShrink: 0,
                              background: colors[i % colors.length],
                            }}
                          />
                          <span
                            style={{
                              fontWeight: 500,
                              color: TEXT,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {v.vendor}
                          </span>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.75rem",
                            flexShrink: 0,
                          }}
                        >
                          <span style={{ fontWeight: 600, color: TEXT }}>
                            RM {v.spend.toLocaleString()}
                          </span>
                          <span
                            style={{
                              width: "3rem",
                              textAlign: "right",
                              fontFamily: "var(--font-display)",
                              fontWeight: 500,
                              color: MUTED,
                            }}
                          >
                            {v.spend_pct.toFixed(1)}%
                          </span>
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

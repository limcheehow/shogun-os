import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { departmentsApi } from "../../../lib/api";
import { DashboardSubNav } from "../DashboardSubNav";
import type {
  DashboardTab,
  ExecutiveApprovalRow,
  ProcurementDashboardStats,
} from "../../../lib/types";
import { ExecutiveProcurementPulseTab } from "./ExecutiveProcurementPulseTab";
import { InventoryCatalogTab } from "./InventoryCatalogTab";
import { PurchaseOrdersVendorTab } from "./PurchaseOrdersVendorTab";
import { AccountingBridgeTab } from "./AccountingBridgeTab";
import { PurchaseRequisitionsTab } from "./PurchaseRequisitionsTab";
import { RfqVendorSourcingTab } from "./RfqVendorSourcingTab";
import { BarcodeScanCounterTab } from "./BarcodeScanCounterTab";
import { ThreeWayMatchTab } from "./ThreeWayMatchTab";
import {
  ProcurementActionModal,
  type ProcurementActionType,
} from "./ProcurementActionModal";

const TABS: DashboardTab[] = [
  { id: "pulse", label: "Overview", icon: "LayoutDashboard" },
  { id: "requisitions", label: "Purchase Requisitions", icon: "FileText" },
  { id: "sourcing", label: "RFQ & Vendor Sourcing", icon: "Award" },
  { id: "po", label: "POs & Vendors", icon: "ClipboardList" },
  { id: "inventory", label: "Inventory", icon: "Package" },
  { id: "barcode", label: "Warehouse & Stock Audit", icon: "Warehouse" },
  { id: "matching", label: "Invoice Matching", icon: "ShieldCheck" },
  { id: "bridge", label: "Accounting Bridge", icon: "Scale" },
];

interface ProcurementDashboardProps {
  department: string;
  color: string;
}

export function ProcurementDashboard({
  department,
  color,
}: ProcurementDashboardProps) {
  const [activeTab, setActiveTab] = useState("pulse");
  const [modalAction, setModalAction] = useState<ProcurementActionType | null>(
    null,
  );
  const [modalEntity, setModalEntity] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [overrideApprovalQueue, setOverrideApprovalQueue] = useState<
    ExecutiveApprovalRow[] | null
  >(null);

  const handleAction = (actionType: string, entity: unknown) => {
    if (actionType === "create_rfq") {
      setActiveTab("sourcing");
      return;
    }
    setModalAction(actionType as ProcurementActionType);
    setModalEntity(entity as Record<string, unknown> | null);
  };

  const handleActionCompleted = (
    actionType: ProcurementActionType,
    entity: Record<string, unknown> | null,
  ) => {
    if (!entity || !entity.po_number) return;
    const poNum = entity.po_number as string;
    let newStatus: ExecutiveApprovalRow["approval_status"] | null = null;
    if (actionType === "approve_po") newStatus = "Approved";
    else if (actionType === "reject_po") newStatus = "Rejected";
    else if (actionType === "request_clarification")
      newStatus = "Clarification Requested";
    else if (actionType === "reply_clarification")
      newStatus = "Pending Executive Approval";

    if (newStatus) {
      const base =
        overrideApprovalQueue ?? statsQuery.data?.executiveApprovalQueue ?? [];
      setOverrideApprovalQueue(
        base.map((item) =>
          item.po_number === poNum
            ? { ...item, approval_status: newStatus! }
            : item,
        ),
      );
    }
  };

  const statsQuery = useQuery({
    queryKey: ["dashboard-procurement-stats", department],
    queryFn: () => departmentsApi.dashboardProcurementStats(department),
    refetchInterval: 120_000,
  });

  if (statsQuery.isLoading) {
    return (
      <div className="flex justify-center py-16 text-slate-400">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const rawStats: ProcurementDashboardStats | undefined = statsQuery.data;

  if (!rawStats) {
    return (
      <div className="flex min-h-[20rem] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
        <p className="text-sm text-slate-500">
          Unable to load Procurement dashboard data.
        </p>
      </div>
    );
  }

  const stats: ProcurementDashboardStats = {
    ...rawStats,
    executiveApprovalQueue:
      overrideApprovalQueue ?? rawStats.executiveApprovalQueue ?? [],
  };

  return (
    <div className="space-y-4">
      <DashboardSubNav tabs={TABS} active={activeTab} onChange={setActiveTab} />

      {activeTab === "pulse" && (
        <ExecutiveProcurementPulseTab
          stats={stats}
          color={color}
          onNavigateTab={setActiveTab}
        />
      )}
      {activeTab === "requisitions" && (
        <PurchaseRequisitionsTab stats={stats} onAction={handleAction} />
      )}
      {activeTab === "sourcing" && (
        <RfqVendorSourcingTab stats={stats} onAction={handleAction} />
      )}
      {activeTab === "po" && (
        <PurchaseOrdersVendorTab
          stats={stats}
          color={color}
          onAction={handleAction}
        />
      )}
      {activeTab === "inventory" && (
        <InventoryCatalogTab
          stats={stats}
          color={color}
          onAction={handleAction}
        />
      )}
      {activeTab === "barcode" && (
        <BarcodeScanCounterTab stats={stats} color={color} />
      )}
      {activeTab === "matching" && (
        <ThreeWayMatchTab stats={stats} onAction={handleAction} />
      )}
      {activeTab === "bridge" && (
        <AccountingBridgeTab
          stats={stats}
          color={color}
          onAction={handleAction}
        />
      )}

      <ProcurementActionModal
        open={modalAction !== null}
        onClose={() => {
          setModalAction(null);
          setModalEntity(null);
        }}
        actionType={modalAction ?? "draft_po"}
        entity={modalEntity}
        department={department}
        onActionCompleted={handleActionCompleted}
      />
    </div>
  );
}

import { AlertTriangle, Package, TrendingDown, TrendingUp } from "lucide-react";
import { BarChart, LineChart } from "../charts";
import type { ProcurementDashboardStats } from "../../../lib/types";

interface Props {
  stats: ProcurementDashboardStats;
  color: string;
  onNavigateTab?: (tabId: string) => void;
}

const fmt = (n: number) =>
  n >= 1_000_000
    ? `RM ${(n / 1_000_000).toFixed(2)}M`
    : n >= 1_000
      ? `RM ${(n / 1_000).toFixed(0)}K`
      : `RM ${n.toFixed(0)}`;

const LOW_STOCK_BADGE = (n: number) => {
  if (n === 0)
    return { label: "Healthy", cls: "bg-emerald-100 text-emerald-700" };
  if (n <= 3) return { label: "Caution", cls: "bg-amber-100 text-amber-700" };
  return { label: "Critical", cls: "bg-rose-100 text-rose-700" };
};

export function ExecutiveProcurementPulseTab({
  stats,
  color,
  onNavigateTab,
}: Props) {
  const lsBadge = LOW_STOCK_BADGE(stats.lowStockAlerts);
  const spendPct =
    stats.procurementSpendBudgetMtd > 0
      ? (stats.procurementSpendMtd / stats.procurementSpendBudgetMtd) * 100
      : 0;
  const deadPct =
    stats.totalInventoryValuation > 0
      ? (stats.deadSlowStockCapital / stats.totalInventoryValuation) * 100
      : 0;

  const KPIs: Array<{
    label: string;
    value: string;
    badge?: { label: string; cls: string };
    sub?: string;
    targetTab?: string;
  }> = [
    {
      label: "Total Inventory Valuation",
      value: fmt(stats.totalInventoryValuation),
    },
    {
      label: "Total Active SKUs",
      value: stats.totalActiveSkus.toLocaleString(),
      targetTab: "inventory",
    },
    {
      label: "Low-Stock Alerts",
      value: `${stats.lowStockAlerts}`,
      badge: lsBadge,
      targetTab: "inventory",
    },
    {
      label: "Dead & Slow Stock Capital",
      value: fmt(stats.deadSlowStockCapital),
      targetTab: "inventory",
    },
    {
      label: "Open Purchase Orders",
      value: `${stats.openPoCount}`,
      sub: fmt(stats.openPoValue),
      targetTab: "requisitions",
    },
    {
      label: "Procurement Spend MTD",
      value: fmt(stats.procurementSpendMtd),
      sub: `of ${fmt(stats.procurementSpendBudgetMtd)} budget`,
    },
  ];

  const SPEND_TREND_SERIES = [
    { key: "spend", label: "Actual Spend", type: "line" as const, color },
    { key: "budget", label: "Budget", type: "line" as const, color: "#94a3b8" },
  ];

  const ALERT_ICON: Record<string, typeof TrendingDown> = {
    safety_breach: AlertTriangle,
    dead_stock: TrendingDown,
    lead_time_delay: TrendingUp,
  };

  const getAlertTargetTab = (type: string, message: string): string => {
    if (type === "safety_breach" || message.includes("safety stock"))
      return "inventory";
    if (type === "dead_stock" || message.includes("slow-moving stock"))
      return "inventory";
    if (
      type === "lead_time_delay" ||
      message.includes("past expected delivery")
    )
      return "po";
    return "inventory";
  };

  return (
    <div className="space-y-4">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {KPIs.map((kpi) => {
          const isClickable = !!kpi.targetTab;
          return (
            <div
              key={kpi.label}
              onClick={() => kpi.targetTab && onNavigateTab?.(kpi.targetTab)}
              className={`card p-4 transition-all ${isClickable ? "cursor-pointer hover:border-brand/60 hover:shadow-md hover:-translate-y-0.5" : ""}`}
            >
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {kpi.label}
              </div>
              <div className="mt-1 text-xl font-bold text-slate-900">
                {kpi.value}
              </div>
              {kpi.badge && (
                <span
                  className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${kpi.badge.cls}`}
                >
                  {kpi.badge.label}
                </span>
              )}
              {kpi.sub && (
                <div className="mt-0.5 text-xs text-slate-500">{kpi.sub}</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Executive Reorder Watchdog Alert Banner */}
      {stats.riskAlerts.length > 0 && (
        <div className="space-y-2">
          {stats.riskAlerts.map((alert, i) => {
            const Icon = ALERT_ICON[alert.type] ?? AlertTriangle;
            const cls =
              alert.level === "critical"
                ? "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100/80"
                : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100/80";
            const targetTab = getAlertTargetTab(alert.type, alert.message);
            return (
              <div
                key={i}
                onClick={() => onNavigateTab?.(targetTab)}
                className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-all cursor-pointer hover:shadow-sm ${cls}`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="flex-1">{alert.message}</span>
                <span className="text-xs font-bold underline opacity-80">
                  View Tab →
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">
            Inventory Valuation by Category
          </h3>
          <BarChart
            data={stats.valuationByCategory}
            xKey="category"
            yKey="value"
            color={color}
            unit="RM "
            height={220}
            dataKeys={["value"]}
            colors={[color]}
          />
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">
            Procurement Spend vs Budget (12 Mo)
          </h3>
          <LineChart
            data={stats.spendVsBudgetTrend}
            xKey="month"
            yKey="spend"
            color={color}
            unit="RM "
            height={220}
            dataKeys={["spend", "budget"]}
            colors={[color, "#94a3b8"]}
            labels={{ spend: "Actual Spend", budget: "Budget" }}
          />
        </div>
      </div>

      {/* Dead Stock & Spend Footers */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card flex items-center justify-between px-5 py-3">
          <div>
            <span className="text-sm font-medium text-slate-600">
              Dead & Slow Stock Capital
            </span>
            <div className="text-xs text-slate-400">
              {deadPct.toFixed(1)}% of total inventory valuation
            </div>
          </div>
          <span
            className={`text-base font-bold ${deadPct > 15 ? "text-rose-600" : "text-slate-800"}`}
          >
            {fmt(stats.deadSlowStockCapital)}
          </span>
        </div>
        <div className="card flex items-center justify-between px-5 py-3">
          <div>
            <span className="text-sm font-medium text-slate-600">
              Procurement Spend MTD
            </span>
            <div className="text-xs text-slate-400">
              {spendPct.toFixed(1)}% of monthly budget
            </div>
          </div>
          <span
            className={`text-base font-bold ${spendPct > 100 ? "text-rose-600" : "text-slate-800"}`}
          >
            {fmt(stats.procurementSpendMtd)}
          </span>
        </div>
      </div>
    </div>
  );
}

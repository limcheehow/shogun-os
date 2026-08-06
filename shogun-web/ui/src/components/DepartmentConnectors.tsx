import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Link2,
  CheckCircle2,
  Loader2,
  BookOpen,
  DollarSign,
  FileText,
  CreditCard,
  Database,
  Plug,
} from "lucide-react";
import toast from "react-hot-toast";
import { connectorsApi } from "../lib/api";
import type { Connector } from "../lib/types";

interface DepartmentConnectorsProps {
  department: string;
}

export default function DepartmentConnectors({
  department,
}: DepartmentConnectorsProps) {
  const [connectingIds, setConnectingIds] = useState<Record<string, boolean>>(
    {},
  );

  const connectorsQuery = useQuery({
    queryKey: ["department-connectors", department],
    queryFn: async () => {
      const res = await connectorsApi.list(department);
      return res.connectors;
    },
  });

  const connectors: Connector[] = connectorsQuery.data || [];

  const handleToggle = async (connector: Connector) => {
    setConnectingIds((prev) => ({ ...prev, [connector.id]: true }));
    try {
      await connectorsApi.toggle(department, connector.id);
      setTimeout(() => {
        setConnectingIds((prev) => ({ ...prev, [connector.id]: false }));
        toast.success(
          connector.status === "connected"
            ? `Disconnected ${connector.name}`
            : `Connected to ${connector.name} successfully!`,
        );
        connectorsQuery.refetch();
      }, 600);
    } catch {
      setConnectingIds((prev) => ({ ...prev, [connector.id]: false }));
      toast.error("Failed to update connector");
    }
  };

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case "BookOpen":
        return BookOpen;
      case "DollarSign":
        return DollarSign;
      case "FileText":
        return FileText;
      case "CreditCard":
        return CreditCard;
      case "Database":
        return Database;
      default:
        return Plug;
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700/50 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white capitalize">
            {department} Integrations & Connectors
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Connect external software, payment gateways, and ERP tools to feed
            live operational data into {department} AI agent.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
          <Plug className="h-4 w-4" />
          {connectors.filter((c) => c.status === "connected").length} Connected
          Software
        </div>
      </div>

      {connectorsQuery.isLoading ? (
        <div className="flex justify-center py-16 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : connectors.length === 0 ? (
        <div className="py-16 text-center text-slate-500 bg-white rounded-xl border border-dashed border-slate-300">
          <Plug className="mx-auto h-10 w-10 text-slate-300 mb-2" />
          <p className="text-sm font-medium">
            No software connectors configured for {department} yet.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {connectors.map((connector) => {
            const IconComp = getIcon(connector.logo_icon);
            const isConnecting = connectingIds[connector.id];
            const isConnected = connector.status === "connected";

            return (
              <div
                key={connector.id}
                className={`flex flex-col justify-between rounded-xl border p-5 transition shadow-sm bg-white dark:bg-slate-900 text-slate-900 dark:text-white ${
                  isConnected
                    ? "border-emerald-300 dark:border-emerald-500/50 ring-1 ring-emerald-300/40"
                    : "border-slate-200 dark:border-slate-800 hover:border-slate-300"
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-11 w-11 items-center justify-center rounded-xl font-bold ${
                          isConnected
                            ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                        }`}
                      >
                        <IconComp className="h-6 w-6" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                          {connector.name}
                        </h3>
                        <span className="text-[11px] font-medium text-slate-400">
                          {connector.category}
                        </span>
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                    {connector.description}
                  </p>

                  {connector.config_summary && (
                    <div className="rounded-md bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 px-2.5 py-1.5 text-[11px] font-mono text-slate-600 dark:text-slate-300 truncate">
                      {connector.config_summary}
                    </div>
                  )}
                </div>

                <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4">
                  {isConnected ? (
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      Connected
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400">
                      Not connected
                    </span>
                  )}

                  <button
                    type="button"
                    onClick={() => handleToggle(connector)}
                    disabled={isConnecting}
                    className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold shadow-sm transition ${
                      isConnected
                        ? "bg-slate-100 text-slate-700 hover:bg-rose-50 hover:text-rose-700"
                        : "bg-brand text-white hover:bg-brand/90"
                    }`}
                  >
                    {isConnecting ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        {isConnected ? "Disconnecting..." : "Connecting..."}
                      </>
                    ) : isConnected ? (
                      "Disconnect"
                    ) : (
                      <>
                        <Link2 className="h-3.5 w-3.5" />
                        Connect
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

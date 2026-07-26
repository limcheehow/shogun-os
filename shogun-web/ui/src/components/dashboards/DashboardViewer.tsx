import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { departmentsApi } from '../../lib/api';
import type { DashboardConfig } from '../../lib/types';
import { CrmDashboard } from './crm/CrmDashboard';

const DASHBOARD_COMPONENTS: Record<string, React.ComponentType<{ department: string; color: string }>> = {
  crm: CrmDashboard,
};

interface DashboardViewerProps {
  department: string;
  color: string;
}

export function DashboardViewer({ department, color }: DashboardViewerProps) {
  const configQuery = useQuery({
    queryKey: ['dashboard-config', department],
    queryFn: () => departmentsApi.dashboardConfig(department),
  });

  if (configQuery.isLoading) {
    return (
      <div className="flex justify-center py-16 text-slate-400">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const config: DashboardConfig | undefined = configQuery.data;
  const DashboardComponent = DASHBOARD_COMPONENTS[department];

  if (!config?.enabled || !DashboardComponent) {
    return (
      <div className="flex min-h-[28rem] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
        <BarChart3 className="mb-3 h-10 w-10 text-slate-300" />
        <h2 className="text-lg font-semibold text-slate-800">Dashboard</h2>
        <p className="mt-1 max-w-sm text-sm text-slate-500">
          No dashboard configured for this department yet.
        </p>
      </div>
    );
  }

  return <DashboardComponent department={department} color={color} />;
}
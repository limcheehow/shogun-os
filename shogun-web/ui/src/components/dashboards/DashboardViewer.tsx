import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { departmentsApi } from '../../lib/api';
import type { DashboardConfig } from '../../lib/types';
import { CrmDashboard } from './crm/CrmDashboard';
import { FinanceDashboard } from './finance/FinanceDashboard';
import { ProcurementDashboard } from './procurement/ProcurementDashboard';

const DASHBOARD_COMPONENTS: Record<string, React.ComponentType<{ department: string; color: string }>> = {
  crm: CrmDashboard,
  finance: FinanceDashboard,
  procurement: ProcurementDashboard,
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
      <div className="sd-empty">
        <div className="h-7 w-7 animate-spin rounded-full" style={{ border: `2px solid var(--samurai-lime)`, borderTopColor: 'transparent' }} />
        <p>Loading dashboard…</p>
      </div>
    );
  }

  const config: DashboardConfig | undefined = configQuery.data;
  const DashboardComponent = DASHBOARD_COMPONENTS[department];

  if (!config?.enabled || !DashboardComponent) {
    return (
      <div className="sd-empty">
        <BarChart3 className="h-10 w-10" style={{ color: 'var(--samurai-muted)' }} />
        <h2>Dashboard</h2>
        <p>No dashboard configured for this department yet.</p>
      </div>
    );
  }

  return <DashboardComponent department={department} color={color} />;
}
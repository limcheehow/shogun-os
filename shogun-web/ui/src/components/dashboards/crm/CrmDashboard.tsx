import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { departmentsApi } from '../../../lib/api';
import { DashboardSubNav } from '../DashboardSubNav';
import type { CeoDashboardStats, DashboardTab } from '../../../lib/types';
import { SalesPulseTab } from './SalesPulseTab';
import { PipelineForecastTab } from './PipelineForecastTab';
import { PartnerPerformanceTab } from './PartnerPerformanceTab';
import { ManagerPerformanceTab } from './ManagerPerformanceTab';
import { DealsDeepDiveTab } from './DealsDeepDiveTab';
import { ManagerDrillDownModal } from './ManagerDrillDownModal';

const TABS: DashboardTab[] = [
  { id: 'revenue', label: 'Sales Booking', icon: 'LayoutDashboard' },
  { id: 'pipeline', label: 'Pipeline & Forecast', icon: 'TrendingUp' },
  { id: 'partner', label: 'Partner Performance', icon: 'Handshake' },
  { id: 'managers', label: 'Manager Performance', icon: 'Users' },
  { id: 'deals', label: 'Deals Deep-Dive', icon: 'Target' },
];

interface CrmDashboardProps {
  department: string;
  color: string;
}

export function CrmDashboard({ department, color }: CrmDashboardProps) {
  const [activeTab, setActiveTab] = useState('revenue');
  const [drillDownOwner, setDrillDownOwner] = useState<string | null>(null);

  const statsQuery = useQuery({
    queryKey: ['dashboard-ceo-stats', department],
    queryFn: () => departmentsApi.dashboardCeoStats(department),
    refetchInterval: 120_000,
  });

  if (statsQuery.isLoading) {
    return (
      <div className="flex justify-center py-16 text-slate-400">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const stats: CeoDashboardStats | undefined = statsQuery.data;

  if (!stats) {
    return (
      <div className="flex min-h-[20rem] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
        <p className="text-sm text-slate-500">Unable to load dashboard data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <DashboardSubNav tabs={TABS} active={activeTab} onChange={setActiveTab} />

      {drillDownOwner && (
        <ManagerDrillDownModal
          owner={drillDownOwner}
          stats={stats}
          color={color}
          onClose={() => setDrillDownOwner(null)}
        />
      )}

      {activeTab === 'revenue' && <SalesPulseTab stats={stats} color={color} />}
      {activeTab === 'pipeline' && <PipelineForecastTab stats={stats} color={color} />}
      {activeTab === 'partner' && <PartnerPerformanceTab stats={stats} color={color} />}
      {activeTab === 'managers' && (
        <ManagerPerformanceTab stats={stats} color={color} onDrillDown={setDrillDownOwner} />
      )}
      {activeTab === 'deals' && <DealsDeepDiveTab stats={stats} color={color} />}
    </div>
  );
}
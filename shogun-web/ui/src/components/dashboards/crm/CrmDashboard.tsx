import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { departmentsApi } from '../../../lib/api';
import { DashboardSubNav } from '../DashboardSubNav';
import type { CeoDashboardStats, DashboardTab } from '../../../lib/types';
import { SalesPulseTab } from './SalesPulseTab';
import { PipelineForecastTab } from './PipelineForecastTab';
import { OmnichannelChatTab } from './OmnichannelChatTab';
import { PartnerPerformanceTab } from './PartnerPerformanceTab';
import { ManagerPerformanceTab } from './ManagerPerformanceTab';
import { DealsDeepDiveTab } from './DealsDeepDiveTab';
import { ManagerDrillDownModal } from './ManagerDrillDownModal';

const TABS: DashboardTab[] = [
  { id: 'revenue', label: 'Sales Booking', icon: 'LayoutDashboard' },
  { id: 'pipeline', label: 'Pipeline & Forecast', icon: 'TrendingUp' },
  { id: 'omnichannel', label: 'Omnichannel Chat', icon: 'MessageCircle' },
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
      <div className="sd-empty">
        <div className="h-7 w-7 animate-spin rounded-full" style={{ border: `2px solid var(--samurai-lime)`, borderTopColor: 'transparent' }} />
        <p>Loading CRM dashboard…</p>
      </div>
    );
  }

  const stats: CeoDashboardStats | undefined = statsQuery.data;

  if (!stats) {
    return (
      <div className="sd-empty">
        <h2>Unable to load CRM dashboard data</h2>
        <p>The CRM snapshot could not be retrieved. Try refreshing the page.</p>
      </div>
    );
  }

  return (
    <div className="sd-stack">
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
      {activeTab === 'omnichannel' && <OmnichannelChatTab stats={stats} color={color} />}
      {activeTab === 'partner' && <PartnerPerformanceTab stats={stats} color={color} />}
      {activeTab === 'managers' && (
        <ManagerPerformanceTab stats={stats} color={color} onDrillDown={setDrillDownOwner} />
      )}
      {activeTab === 'deals' && <DealsDeepDiveTab stats={stats} color={color} />}
    </div>
  );
}
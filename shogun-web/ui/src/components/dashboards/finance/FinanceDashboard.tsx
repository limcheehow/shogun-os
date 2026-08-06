import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { departmentsApi } from '../../../lib/api';
import { DashboardSubNav } from '../DashboardSubNav';
import type { DashboardTab, FinanceDashboardStats } from '../../../lib/types';
import { ExecutivePulseTab } from './ExecutivePulseTab';
import { CashRunwayTab } from './CashRunwayTab';
import { WorkingCapitalOpsTab } from './WorkingCapitalOpsTab';
import { BvaUnitEconomicsTab } from './BvaUnitEconomicsTab';
import { CloseTaxComplianceTab } from './CloseTaxComplianceTab';

const TABS: DashboardTab[] = [
  { id: 'pulse',      label: 'Executive Pulse',   icon: 'LayoutDashboard' },
  { id: 'runway',     label: 'Cash & Runway',      icon: 'TrendingUp' },
  { id: 'ops',        label: 'AR & AP Ops',        icon: 'Receipt' },
  { id: 'bva',        label: 'Budget vs Actuals',  icon: 'BarChart3' },
  { id: 'compliance', label: 'Close & Tax',        icon: 'ShieldCheck' },
];

interface FinanceDashboardProps {
  department: string;
  color: string;
}

export function FinanceDashboard({ department, color }: FinanceDashboardProps) {
  const [activeTab, setActiveTab] = useState('pulse');

  const statsQuery = useQuery({
    queryKey: ['dashboard-finance-stats', department],
    queryFn: () => departmentsApi.dashboardFinanceStats(department),
    refetchInterval: 120_000,
  });

  if (statsQuery.isLoading) {
    return (
      <div className="sd-empty">
        <div className="h-7 w-7 animate-spin rounded-full" style={{ border: `2px solid var(--samurai-lime)`, borderTopColor: 'transparent' }} />
        <p>Loading Finance dashboard…</p>
      </div>
    );
  }

  const stats: FinanceDashboardStats | undefined = statsQuery.data;

  if (!stats) {
    return (
      <div className="sd-empty">
        <h2>Unable to load Finance dashboard data</h2>
        <p>The finance snapshot could not be retrieved. Try refreshing the page.</p>
      </div>
    );
  }

  return (
    <div className="sd-stack">
      <DashboardSubNav tabs={TABS} active={activeTab} onChange={setActiveTab} />

      <div>
        {activeTab === 'pulse'      && <ExecutivePulseTab stats={stats} color={color} />}
        {activeTab === 'runway'     && <CashRunwayTab stats={stats} color={color} />}
        {activeTab === 'ops'        && <WorkingCapitalOpsTab stats={stats} color={color} />}
        {activeTab === 'bva'        && <BvaUnitEconomicsTab stats={stats} color={color} />}
        {activeTab === 'compliance' && <CloseTaxComplianceTab stats={stats} color={color} />}
      </div>
    </div>
  );
}
import clsx from 'clsx';
import type { DashboardTab } from '../../lib/types';

interface DashboardSubNavProps {
  tabs: DashboardTab[];
  active: string;
  onChange: (id: string) => void;
}

export function DashboardSubNav({ tabs, active, onChange }: DashboardSubNavProps) {
  return (
    <div className="sd-subnav-bar">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={clsx('sd-subnav-pill', active === tab.id && 'active')}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
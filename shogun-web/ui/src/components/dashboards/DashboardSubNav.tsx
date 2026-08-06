import clsx from 'clsx';
import type { DashboardTab } from '../../lib/types';

interface DashboardSubNavProps {
  tabs: DashboardTab[];
  active: string;
  onChange: (id: string) => void;
}

export function DashboardSubNav({ tabs, active, onChange }: DashboardSubNavProps) {
  return (
    <div className="flex flex-wrap gap-1.5 py-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
            active === tab.id
              ? 'bg-brand text-white shadow-sm'
              : 'bg-white text-slate-600 border border-surface-border hover:border-slate-300 hover:bg-slate-50',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
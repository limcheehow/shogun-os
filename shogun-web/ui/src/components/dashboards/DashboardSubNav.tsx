import clsx from 'clsx';
import type { DashboardTab } from '../../lib/types';

interface DashboardSubNavProps {
  tabs: DashboardTab[];
  active: string;
  onChange: (id: string) => void;
}

export function DashboardSubNav({ tabs, active, onChange }: DashboardSubNavProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={clsx(
            'shrink-0 flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-medium transition-all whitespace-nowrap',
            active === tab.id
              ? 'bg-brand text-white shadow-sm'
              : 'bg-white text-slate-500 border border-surface-border hover:border-slate-300',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
import { useEffect } from 'react';
import { X } from 'lucide-react';
import type { CeoDashboardStats } from '../../../lib/types';

interface ManagerDrillDownModalProps {
  owner: string;
  stats: CeoDashboardStats;
  color: string;
  onClose: () => void;
}

export function ManagerDrillDownModal({ owner, stats, color, onClose }: ManagerDrillDownModalProps) {
  const mgr = stats.byManager.find((m) => m.owner === owner);
  const atRisk = stats.atRiskByManager.find((r) => r.owner === owner);
  const topDeals = stats.topDeals.filter((d) => d.owner === owner);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!mgr) return null;

  return (
    <>
      {/* Backdrop */}
      <button type="button" className="fixed inset-0 z-40 cursor-default bg-black/30" onClick={onClose} aria-label="Close" />
      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16" onClick={onClose}>
        <div
          className="card relative z-50 w-full max-w-lg overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900">{owner}</h2>
              <p className="text-xs text-slate-500">Manager drill-down</p>
            </div>
            <button type="button" onClick={onClose} className="btn-ghost !px-2 !py-1" aria-label="Close">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* KPI mini-cards */}
          <div className="grid grid-cols-3 gap-2 px-5 py-4">
            <div className="rounded-lg bg-surface-muted p-3 text-center">
              <div className="text-xs font-medium text-slate-500">YTD</div>
              <div className="text-base font-bold text-slate-900">RM {(mgr.salesYTD / 1000).toFixed(0)}K</div>
            </div>
            <div className="rounded-lg bg-surface-muted p-3 text-center">
              <div className="text-xs font-medium text-slate-500">Pipeline</div>
              <div className="text-base font-bold text-slate-900">RM {(mgr.pipelineValue / 1000).toFixed(0)}K</div>
            </div>
            <div className="rounded-lg bg-surface-muted p-3 text-center">
              <div className="text-xs font-medium text-slate-500">Win Rate</div>
              <div className="text-base font-bold text-slate-900">{mgr.winRate}%</div>
            </div>
            <div className="rounded-lg bg-surface-muted p-3 text-center">
              <div className="text-xs font-medium text-slate-500">Deals</div>
              <div className="text-base font-bold text-slate-900">{mgr.deals}</div>
            </div>
            <div className="rounded-lg bg-surface-muted p-3 text-center">
              <div className="text-xs font-medium text-slate-500">Won</div>
              <div className="text-base font-bold text-slate-900">{mgr.wonDeals}</div>
            </div>
            <div className="rounded-lg bg-surface-muted p-3 text-center">
              <div className="text-xs font-medium text-slate-500">Weighted</div>
              <div className="text-base font-bold text-slate-900">RM {(mgr.weightedPipeline / 1000).toFixed(0)}K</div>
            </div>
          </div>

          {/* Closing soon */}
          {(mgr.closeThisMonth > 0 || mgr.closeThisQ > 0) && (
            <div className="border-t border-surface-border px-5 py-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Closing Soon</div>
              <div className="mt-1 flex gap-4 text-sm">
                {mgr.closeThisMonth > 0 && (
                  <span>This month: <strong className="text-slate-900">RM {(mgr.closeThisMonth / 1000).toFixed(0)}K</strong></span>
                )}
                {mgr.closeThisQ > 0 && (
                  <span>This Q: <strong className="text-slate-900">RM {(mgr.closeThisQ / 1000).toFixed(0)}K</strong></span>
                )}
              </div>
            </div>
          )}

          {/* At-risk */}
          {atRisk && atRisk.atRiskDeals > 0 && (
            <div className="border-t border-surface-border px-5 py-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-rose-600">At Risk</span>
                <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">
                  {atRisk.atRiskDeals} deals
                </span>
              </div>
              <p className="mt-1 text-sm text-rose-700">
                RM {(atRisk.atRiskValue / 1000).toFixed(0)}K in stalled deals
              </p>
            </div>
          )}

          {/* Top deals */}
          {topDeals.length > 0 && (
            <div className="border-t border-surface-border px-5 py-3">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Top Deals ({topDeals.length})
              </div>
              <div className="space-y-1">
                {topDeals.slice(0, 5).map((d) => (
                  <div key={d.slug} className="flex items-center justify-between rounded-md bg-surface-muted px-3 py-1.5">
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-slate-900">{d.title}</div>
                      <div className="text-xs text-slate-500">{d.customer} · {d.stage}</div>
                    </div>
                    <div className="ml-3 text-right text-sm font-semibold text-slate-900">
                      RM {(d.amount / 1000).toFixed(0)}K
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
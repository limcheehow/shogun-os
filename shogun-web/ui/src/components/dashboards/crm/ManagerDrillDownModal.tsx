import { useEffect } from 'react';
import { X } from 'lucide-react';
import type { CeoDashboardStats } from '../../../lib/types';

interface ManagerDrillDownModalProps {
  owner: string;
  stats: CeoDashboardStats;
  color: string;
  onClose: () => void;
}

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const SURFACE_2 = 'var(--samurai-surface-2)';
const BORDER = 'var(--samurai-border)';

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

  const miniKpis = [
    { label: 'YTD', value: `RM ${(mgr.salesYTD / 1000).toFixed(0)}K` },
    { label: 'Pipeline', value: `RM ${(mgr.pipelineValue / 1000).toFixed(0)}K` },
    { label: 'Win Rate', value: `${mgr.winRate}%` },
    { label: 'Deals', value: `${mgr.deals}` },
    { label: 'Won', value: `${mgr.wonDeals}` },
    { label: 'Weighted', value: `RM ${(mgr.weightedPipeline / 1000).toFixed(0)}K` },
  ];

  return (
    <>
      {/* Backdrop */}
      <button
        type="button"
        className="fixed inset-0 z-40"
        style={{ background: 'rgba(0,0,0,0.4)', border: 'none', cursor: 'default' }}
        onClick={onClose}
        aria-label="Close"
      />
      {/* Modal */}
      <div
        className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16"
        onClick={onClose}
      >
        <div
          className="sd-card relative z-50 w-full"
          style={{ maxWidth: '28rem' }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-5 py-4"
            style={{ borderBottom: `1px solid ${BORDER}` }}
          >
            <div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: TEXT, margin: 0 }}>{owner}</h2>
              <p style={{ fontSize: '0.72rem', color: MUTED, margin: 0 }}>Manager drill-down</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="sd-btn sd-btn-ghost"
              style={{ padding: '0.3rem 0.5rem' }}
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* KPI mini-cards */}
          <div className="grid grid-cols-3 gap-2 px-5 py-4">
            {miniKpis.map((kpi) => (
              <div key={kpi.label} className="rounded-lg p-3 text-center" style={{ background: SURFACE_2 }}>
                <div style={{ fontSize: '0.66rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED }}>{kpi.label}</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.95rem', fontWeight: 600, color: TEXT, marginTop: '0.2rem' }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* Closing soon */}
          {(mgr.closeThisMonth > 0 || mgr.closeThisQ > 0) && (
            <div className="px-5 py-3" style={{ borderTop: `1px solid ${BORDER}` }}>
              <div style={{ fontSize: '0.66rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED }}>Closing Soon</div>
              <div className="mt-1 flex gap-4 text-sm">
                {mgr.closeThisMonth > 0 && (
                  <span style={{ color: MUTED }}>This month: <strong style={{ color: TEXT }}>RM {(mgr.closeThisMonth / 1000).toFixed(0)}K</strong></span>
                )}
                {mgr.closeThisQ > 0 && (
                  <span style={{ color: MUTED }}>This Q: <strong style={{ color: TEXT }}>RM {(mgr.closeThisQ / 1000).toFixed(0)}K</strong></span>
                )}
              </div>
            </div>
          )}

          {/* At-risk */}
          {atRisk && atRisk.atRiskDeals > 0 && (
            <div className="px-5 py-3" style={{ borderTop: `1px solid ${BORDER}` }}>
              <div className="flex items-center gap-2">
                <span style={{ fontSize: '0.66rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--samurai-danger)' }}>At Risk</span>
                <span className="sd-chip bad">{atRisk.atRiskDeals} deals</span>
              </div>
              <p className="mt-1 text-sm" style={{ color: 'var(--samurai-danger)' }}>
                RM {(atRisk.atRiskValue / 1000).toFixed(0)}K in stalled deals
              </p>
            </div>
          )}

          {/* Top deals */}
          {topDeals.length > 0 && (
            <div className="px-5 py-3" style={{ borderTop: `1px solid ${BORDER}` }}>
              <div style={{ fontSize: '0.66rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: MUTED, marginBottom: '0.5rem' }}>
                Top Deals ({topDeals.length})
              </div>
              <div className="sd-stack" style={{ gap: '0.25rem' }}>
                {topDeals.slice(0, 5).map((d) => (
                  <div key={d.slug} className="flex items-center justify-between rounded-md px-3 py-1.5" style={{ background: SURFACE_2 }}>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm" style={{ fontWeight: 600, color: TEXT }}>{d.title}</div>
                      <div style={{ fontSize: '0.72rem', color: MUTED }}>{d.customer} · {d.stage}</div>
                    </div>
                    <div className="ml-3 text-right text-sm" style={{ fontWeight: 600, color: TEXT }}>
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

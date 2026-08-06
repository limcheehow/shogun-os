import { CheckCircle2, Link2, XCircle } from 'lucide-react';
import type { ProcurementDashboardStats } from '../../../lib/types';

interface Props {
  stats: ProcurementDashboardStats;
  color: string;
  onAction?: (actionType: string, entity: unknown) => void;
}

const fmtMyr = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const SYNC_STYLE: Record<string, string> = {
  'Ready to Sync':    'warn',
  'Synced to Bukku':  'ok',
  'Sync Error':       'bad',
};

const RECON_STYLE: Record<string, string> = {
  'Reconciled':       'ok',
  'Variance Flagged': 'bad',
};

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const BORDER = 'var(--samurai-border)';
const SURFACE_2 = 'var(--samurai-surface-2)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

export function AccountingBridgeTab({ stats, onAction }: Props) {
  const bridge = stats.accountingBridge;
  const bridgeState = bridge.enabled && bridge.connected ? 'connected' : bridge.enabled ? 'pending' : 'disabled';
  const bridgeChip = bridgeState === 'connected' ? 'ok' : bridgeState === 'pending' ? 'warn' : 'muted';

  return (
    <div className="sd-stack">
      {/* Accounting Bridge Status Indicator Widget */}
      <div className="sd-card">
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              display: 'flex', height: '2.5rem', width: '2.5rem', alignItems: 'center', justifyContent: 'center', borderRadius: '999px',
              background: bridgeState === 'connected' ? 'color-mix(in srgb, var(--samurai-ok) 16%, transparent)' : bridgeState === 'pending' ? 'color-mix(in srgb, var(--samurai-warning) 18%, transparent)' : SURFACE_2,
            }}>
              {bridgeState === 'connected' ? (
                <CheckCircle2 className="h-5 w-5" style={{ color: 'var(--samurai-ok)' }} />
              ) : bridgeState === 'pending' ? (
                <Link2 className="h-5 w-5" style={{ color: 'var(--samurai-warning)' }} />
              ) : (
                <XCircle className="h-5 w-5" style={{ color: MUTED }} />
              )}
            </div>
            <div>
              <h3 className="sd-chart-title" style={{ margin: 0 }}>Accounting Bridge Sync</h3>
              <p style={{ fontSize: '0.72rem', color: MUTED, margin: 0 }}>
                ENABLE_ACCOUNTING_SYNC = <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, color: bridge.enabled ? 'var(--samurai-ok)' : MUTED }}>{bridge.enabled ? 'true' : 'false'}</span>
                {bridge.provider !== 'None' && <> · Provider: {bridge.provider}</>}
                {bridge.last_sync && <> · Last sync: {bridge.last_sync}</>}
              </p>
            </div>
          </div>
          <span className={`sd-chip ${bridgeChip}`}>
            {bridgeState === 'connected' ? 'Connected' : bridgeState === 'pending' ? 'Enabled — Not Connected' : 'Disabled'}
          </span>
        </div>
        {!bridge.enabled && (
          <p style={{ marginTop: '0.75rem', fontSize: '0.72rem', color: MUTED }}>
            Set <code style={{ borderRadius: '0.25rem', background: SURFACE_2, padding: '0.1rem 0.25rem', fontFamily: 'var(--font-display)' }}>ENABLE_ACCOUNTING_SYNC=true</code> and configure a provider (Bukku / QBO / Xero) to enable PO-to-Bill conversion and GL valuation reconciliation.
          </p>
        )}
      </div>

      {/* PO-to-Purchase Bill Automated Conversion Queue */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">PO → Purchase Bill Conversion Queue</h3>
        {stats.poBillConversionQueue.length === 0 ? (
          <p style={{ color: MUTED, fontSize: '0.85rem' }}>
            {bridge.enabled
              ? 'No received POs awaiting conversion to AP Bills.'
              : 'Accounting bridge disabled — enable sync to queue received POs for AP Bill conversion.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">PO #</Th>
                  <Th align="left">Vendor</Th>
                  <Th align="left">Date Received</Th>
                  <Th align="right">Total Amount</Th>
                  <Th align="center">Sync Status</Th>
                  <Th align="center">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {stats.poBillConversionQueue.map((row) => (
                  <tr key={row.po_number} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-3 py-2" style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', fontWeight: 600, color: TEXT }}>{row.po_number}</td>
                    <td className="px-3 py-2" style={{ fontWeight: 600, color: TEXT }}>{row.vendor}</td>
                    <td className="px-3 py-2" style={{ color: MUTED }}>{row.date_received}</td>
                    <td className="px-3 py-2 text-right" style={{ fontWeight: 600, color: TEXT }}>{fmtMyr(row.total_amount)}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={`sd-chip ${SYNC_STYLE[row.sync_status] ?? 'muted'}`}>
                        {row.sync_status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '0.25rem' }}>
                        {row.sync_status === 'Synced to Bukku' ? (
                          <button type="button" onClick={() => onAction?.('view_grn', row)} className="sd-btn sd-btn-ghost" style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}>View GRN Match</button>
                        ) : (
                          <>
                            <button type="button" onClick={() => onAction?.('sync_bill', row)} className="sd-btn sd-btn-primary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}>Sync Bill</button>
                            <button type="button" onClick={() => onAction?.('view_grn', row)} className="sd-btn sd-btn-ghost" style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }}>View GRN</button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inventory GL Valuation Reconciliation Table */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Inventory GL Valuation Reconciliation</h3>
        <p className="sd-chart-sub">
          Compares physical inventory valuation in G-Brain against General Ledger Inventory Account (Code 1400).
        </p>
        {stats.glValuationReconciliation.length === 0 ? (
          <p style={{ color: MUTED, fontSize: '0.85rem' }}>
            {bridge.enabled
              ? 'No GL reconciliation data yet. Chotatsu runs weekly-inventory-valuation to compute physical stock value.'
              : 'Accounting bridge disabled — enable sync to reconcile physical stock value against the GL.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">GL Account</Th>
                  <Th align="right">Physical Stock Value</Th>
                  <Th align="right">GL Book Value</Th>
                  <Th align="right">Variance</Th>
                  <Th align="right">Variance %</Th>
                  <Th align="center">Status</Th>
                </tr>
              </thead>
              <tbody>
                {stats.glValuationReconciliation.map((row) => (
                  <tr key={row.account_code} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td className="px-3 py-2" style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', fontWeight: 600, color: TEXT }}>{row.account_code}</td>
                    <td className="px-3 py-2 text-right" style={{ color: TEXT }}>{fmtMyr(row.physical_stock_value)}</td>
                    <td className="px-3 py-2 text-right" style={{ color: TEXT }}>{fmtMyr(row.gl_book_value)}</td>
                    <td className="px-3 py-2 text-right" style={{ fontWeight: 600, color: Math.abs(row.variance) > 1 ? 'var(--samurai-danger)' : 'var(--samurai-ok)' }}>
                      {row.variance >= 0 ? '+' : ''}{fmtMyr(row.variance)}
                    </td>
                    <td className="px-3 py-2 text-right" style={{ fontWeight: 600, color: Math.abs(row.variance_pct) > 1 ? 'var(--samurai-danger)' : 'var(--samurai-ok)' }}>
                      {row.variance_pct >= 0 ? '+' : ''}{row.variance_pct.toFixed(2)}%
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`sd-chip ${RECON_STYLE[row.reconciliation_status] ?? 'muted'}`}>
                        {row.reconciliation_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

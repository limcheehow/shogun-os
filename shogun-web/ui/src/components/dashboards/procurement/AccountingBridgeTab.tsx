import { CheckCircle2, Link2, XCircle } from 'lucide-react';
import type { ProcurementDashboardStats } from '../../../lib/types';

interface Props {
  stats: ProcurementDashboardStats;
  color: string;
  onAction?: (actionType: string, entity: unknown) => void;
}

const fmtMyr = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const SYNC_STYLE: Record<string, string> = {
  'Ready to Sync':    'bg-amber-100 text-amber-700',
  'Synced to Bukku':  'bg-emerald-100 text-emerald-700',
  'Sync Error':       'bg-rose-100 text-rose-700',
};

const RECON_STYLE: Record<string, string> = {
  'Reconciled':       'bg-emerald-100 text-emerald-700',
  'Variance Flagged': 'bg-rose-100 text-rose-700',
};

export function AccountingBridgeTab({ stats, onAction }: Props) {
  const bridge = stats.accountingBridge;

  return (
    <div className="space-y-4">
      {/* Accounting Bridge Status Indicator Widget */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-full ${bridge.enabled && bridge.connected ? 'bg-emerald-100' : bridge.enabled ? 'bg-amber-100' : 'bg-slate-100'}`}>
              {bridge.enabled && bridge.connected ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              ) : bridge.enabled ? (
                <Link2 className="h-5 w-5 text-amber-600" />
              ) : (
                <XCircle className="h-5 w-5 text-slate-400" />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700">Accounting Bridge Sync</h3>
              <p className="text-xs text-slate-500">
                ENABLE_ACCOUNTING_SYNC = <span className={`font-mono font-semibold ${bridge.enabled ? 'text-emerald-600' : 'text-slate-400'}`}>{bridge.enabled ? 'true' : 'false'}</span>
                {bridge.provider !== 'None' && <> · Provider: {bridge.provider}</>}
                {bridge.last_sync && <> · Last sync: {bridge.last_sync}</>}
              </p>
            </div>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
            bridge.enabled && bridge.connected ? 'bg-emerald-100 text-emerald-700' :
            bridge.enabled ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'
          }`}>
            {bridge.enabled && bridge.connected ? 'Connected' : bridge.enabled ? 'Enabled — Not Connected' : 'Disabled'}
          </span>
        </div>
        {!bridge.enabled && (
          <p className="mt-3 text-xs text-slate-400">
            Set <code className="rounded bg-surface-muted px-1 py-0.5 font-mono">ENABLE_ACCOUNTING_SYNC=true</code> and configure a provider (Bukku / QBO / Xero) to enable PO-to-Bill conversion and GL valuation reconciliation.
          </p>
        )}
      </div>

      {/* PO-to-Purchase Bill Automated Conversion Queue */}
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">PO → Purchase Bill Conversion Queue</h3>
        {stats.poBillConversionQueue.length === 0 ? (
          <p className="text-sm text-slate-400">
            {bridge.enabled
              ? 'No received POs awaiting conversion to AP Bills.'
              : 'Accounting bridge disabled — enable sync to queue received POs for AP Bill conversion.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">PO #</th>
                  <th className="pb-2 text-left font-medium">Vendor</th>
                  <th className="pb-2 text-left font-medium">Date Received</th>
                  <th className="pb-2 text-right font-medium">Total Amount</th>
                  <th className="pb-2 text-center font-medium">Sync Status</th>
                  <th className="pb-2 text-center font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.poBillConversionQueue.map((row) => (
                  <tr key={row.po_number} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-mono text-xs font-medium text-slate-800">{row.po_number}</td>
                    <td className="py-2 font-medium text-slate-800">{row.vendor}</td>
                    <td className="py-2 text-slate-600">{row.date_received}</td>
                    <td className="py-2 text-right font-semibold text-slate-900">{fmtMyr(row.total_amount)}</td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${SYNC_STYLE[row.sync_status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {row.sync_status}
                      </span>
                    </td>
                    <td className="py-2 text-center">
                      <div className="flex justify-center gap-1">
                        {row.sync_status === 'Synced to Bukku' ? (
                          <button type="button" onClick={() => onAction?.('view_grn', row)} className="rounded-md bg-surface-muted px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200 transition-colors">View GRN Match</button>
                        ) : (
                          <>
                            <button type="button" onClick={() => onAction?.('sync_bill', row)} className="rounded-md bg-brand px-2.5 py-1 text-xs font-medium text-white hover:opacity-90 transition-opacity">Sync Bill</button>
                            <button type="button" onClick={() => onAction?.('view_grn', row)} className="rounded-md bg-surface-muted px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200 transition-colors">View GRN</button>
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
      <div className="card p-4">
        <h3 className="mb-1 text-sm font-semibold text-slate-700">Inventory GL Valuation Reconciliation</h3>
        <p className="mb-3 text-xs text-slate-400">
          Compares physical inventory valuation in G-Brain against General Ledger Inventory Account (Code 1400).
        </p>
        {stats.glValuationReconciliation.length === 0 ? (
          <p className="text-sm text-slate-400">
            {bridge.enabled
              ? 'No GL reconciliation data yet. Chotatsu runs weekly-inventory-valuation to compute physical stock value.'
              : 'Accounting bridge disabled — enable sync to reconcile physical stock value against the GL.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs text-slate-500">
                  <th className="pb-2 text-left font-medium">GL Account</th>
                  <th className="pb-2 text-right font-medium">Physical Stock Value</th>
                  <th className="pb-2 text-right font-medium">GL Book Value</th>
                  <th className="pb-2 text-right font-medium">Variance</th>
                  <th className="pb-2 text-right font-medium">Variance %</th>
                  <th className="pb-2 text-center font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {stats.glValuationReconciliation.map((row) => (
                  <tr key={row.account_code} className="hover:bg-surface-muted/50">
                    <td className="py-2 font-mono text-xs font-medium text-slate-800">{row.account_code}</td>
                    <td className="py-2 text-right text-slate-700">{fmtMyr(row.physical_stock_value)}</td>
                    <td className="py-2 text-right text-slate-700">{fmtMyr(row.gl_book_value)}</td>
                    <td className={`py-2 text-right font-semibold ${Math.abs(row.variance) > 1 ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {row.variance >= 0 ? '+' : ''}{fmtMyr(row.variance)}
                    </td>
                    <td className={`py-2 text-right font-semibold ${Math.abs(row.variance_pct) > 1 ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {row.variance_pct >= 0 ? '+' : ''}{row.variance_pct.toFixed(2)}%
                    </td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${RECON_STYLE[row.reconciliation_status] ?? 'bg-slate-100 text-slate-600'}`}>
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

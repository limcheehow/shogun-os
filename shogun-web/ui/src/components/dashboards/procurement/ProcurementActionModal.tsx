import { useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { useChatSocket } from '../../../lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export type ProcurementActionType =
  | 'edit_sku'
  | 'record_adjustment'
  | 'draft_po'
  | 'approve_po'
  | 'reject_po'
  | 'request_clarification'
  | 'reply_clarification'
  | 'trigger_liquidation'
  | 'initiate_return'
  | 'sync_bill'
  | 'view_grn'
  | 'receive_grn'
  | 'send_reminder'
  | 'cancel_po';

interface Entity {
  [k: string]: unknown;
}

interface Props {
  open: boolean;
  onClose: () => void;
  actionType: ProcurementActionType;
  entity: Entity | null;
  department?: string;
  onActionCompleted?: (actionType: ProcurementActionType, entity: Entity | null) => void;
}

const ACTION_TITLE: Record<ProcurementActionType, string> = {
  edit_sku: 'Edit SKU',
  record_adjustment: 'Record Stock Adjustment',
  draft_po: 'Draft Purchase Order',
  approve_po: 'Approve PO',
  reject_po: 'Reject PO',
  request_clarification: 'Request Clarification',
  reply_clarification: 'Reply Clarification & Resubmit',
  trigger_liquidation: 'Trigger Liquidation Campaign',
  initiate_return: 'Initiate Vendor Return',
  sync_bill: 'Sync Bill to Accounting',
  view_grn: 'View GRN Match',
  receive_grn: 'Receive Goods (GRN)',
  send_reminder: 'Send Vendor Reminder',
  cancel_po: 'Cancel PO',
};

function fmtMyr(n: number) {
  return `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function entitySummary(entity: Entity | null): string {
  if (!entity) return 'No entity context.';
  const parts: string[] = [];
  const po = entity.po_number as string | undefined;
  const sku = entity.sku as string | undefined;
  const vendor = (entity.vendor as string | undefined) || (entity.name as string | undefined);
  const amt = typeof entity.total_amount === 'number' ? entity.total_amount : undefined;
  if (po) parts.push(`PO ${po}`);
  if (sku) parts.push(`SKU ${sku}`);
  if (vendor) parts.push(vendor);
  if (amt !== undefined) parts.push(fmtMyr(amt));
  return parts.length ? parts.join(' · ') : 'No entity context.';
}

function defaultInstruction(actionType: ProcurementActionType, entity: Entity | null): string {
  const po = (entity?.po_number as string) || '';
  const vendor = (entity?.vendor as string) || '';
  const sku = (entity?.sku as string) || '';
  const amt = typeof entity?.total_amount === 'number' ? fmtMyr(entity.total_amount) : '';
  switch (actionType) {
    case 'approve_po':
      return `PO ${po} to ${vendor} for ${amt} is awaiting executive sign-off. Approve and issue to vendor.`;
    case 'reject_po':
      return `PO ${po} to ${vendor} for ${amt} is awaiting executive sign-off. Reject this requisition and document the reason.`;
    case 'request_clarification':
      return `PO ${po} to ${vendor} for ${amt} needs clarification before executive sign-off. Request details from the requester.`;
    case 'reply_clarification':
      return `Provide requested clarification details for PO ${po} to ${vendor}. Resubmit PO status back to 'Pending Executive Approval' for executive sign-off.`;
    case 'draft_po':
      return `Draft a purchase order for SKU ${sku}. Confirm quantity, preferred vendor, and expected delivery.`;
    case 'edit_sku':
      return `Update the record for SKU ${sku}. Specify the fields to change (cost, reorder point, location).`;
    case 'record_adjustment':
      return `Record a stock adjustment for SKU ${sku}. Specify delta and reason.`;
    case 'trigger_liquidation':
      return `Trigger a liquidation campaign for the dead/slow-moving SKU ${sku}. Recommend a discount or bundle.`;
    case 'initiate_return':
      return `Initiate a vendor clearance return for SKU ${sku}. State return quantity and vendor RMA reference.`;
    case 'sync_bill':
      return `Sync the purchase bill for PO ${po} to the accounting provider. Confirm the GL posting.`;
    case 'view_grn':
      return `Show the GRN match details for PO ${po}.`;
    case 'receive_grn':
      return `Record goods received (GRN) for PO ${po}. State received quantity and condition.`;
    case 'send_reminder':
      return `Send a delivery reminder to ${vendor} for PO ${po}.`;
    case 'cancel_po':
      return `Cancel PO ${po} to ${vendor}. Document the cancellation reason.`;
    default:
      return '';
  }
}

export function buildActionPrompt(actionType: ProcurementActionType, entity: Entity | null, instruction: string): string {
  const title = ACTION_TITLE[actionType];
  const summary = entitySummary(entity);
  const instr = instruction.trim();
  return `Action: ${title}\nContext: ${summary}\nInstruction: ${instr}`;
}

export function ProcurementActionModal({ open, onClose, actionType, entity, department = 'procurement', onActionCompleted }: Props) {
  const [instruction, setInstruction] = useState('');
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const [proxyError, setProxyError] = useState<string | null>(null);
  const replyRef = useRef<HTMLDivElement | null>(null);
  const sentRef = useRef(false);

  useEffect(() => {
    if (open) {
      setInstruction(defaultInstruction(actionType, entity));
      setReply('');
      setProxyError(null);
      setSending(false);
      sentRef.current = false;
    }
  }, [open, actionType, entity]);

  const { connected, send } = useChatSocket(department, {
    onEvent: (event) => {
      if (event.type === 'delta') {
        setReply((prev) => prev + event.content);
      } else if (event.type === 'message') {
        setReply(event.message?.content || '');
        setSending(false);
      } else if (event.type === 'done') {
        setSending(false);
      } else if (event.type === 'error') {
        setProxyError(event.message || 'Agent error');
        setSending(false);
      }
    },
  });

  useEffect(() => {
    if (open) replyRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [reply, open]);

  const title = useMemo(() => ACTION_TITLE[actionType], [actionType]);

  const handleConfirm = () => {
    onActionCompleted?.(actionType, entity);
    if (!connected) {
      setProxyError('Agent gateway is not connected. Start the procurement-manager gateway and try again.');
      return;
    }
    const prompt = buildActionPrompt(actionType, entity, instruction);
    try {
      send(prompt);
      setSending(true);
      setProxyError(null);
      sentRef.current = true;
    } catch (err) {
      setProxyError(err instanceof Error ? err.message : 'Failed to dispatch');
      setSending(false);
    }
  };

  const MUTED = 'var(--samurai-muted)';
  const TEXT = 'var(--samurai-text)';
  const BORDER = 'var(--samurai-border)';
  const SURFACE_2 = 'var(--samurai-surface-2)';

  if (!open) return null;

  return (
    <button
      type="button"
      style={{ position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(0,0,0,0.4)', border: 'none', cursor: 'default', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
      onClick={onClose}
      aria-label="Close"
    >
      <div
        className="sd-card"
        style={{ position: 'relative', zIndex: 50, width: '100%', maxWidth: '38rem', height: 'fit-content', padding: '1.25rem' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${BORDER}`, paddingBottom: '0.75rem', marginBottom: '0.75rem' }}>
          <div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '0.95rem', fontWeight: 600, color: TEXT, margin: 0 }}>{title}</h3>
            <p style={{ fontSize: '0.72rem', color: MUTED, margin: 0 }}>{entitySummary(entity)}</p>
          </div>
          <button type="button" className="sd-icon-btn" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="sd-stack" style={{ gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.72rem', color: MUTED }}>
            {connected ? (
              <span className="sd-chip ok">Gateway connected</span>
            ) : (
              <span className="sd-chip bad">Gateway not connected</span>
            )}
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: MUTED, marginBottom: '0.375rem' }}>Instruction</label>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              rows={4}
              style={{ width: '100%', borderRadius: '0.5rem', border: `1px solid ${BORDER}`, background: 'var(--samurai-surface)', padding: '0.5rem 0.75rem', fontSize: '0.85rem', color: TEXT, fontFamily: 'var(--font-body)' }}
            />
          </div>

          {(reply || sending) && (
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 500, color: MUTED, marginBottom: '0.375rem' }}>Agent reply</label>
              <div style={{ maxHeight: '16rem', overflowY: 'auto', borderRadius: '0.5rem', border: `1px solid ${BORDER}`, background: SURFACE_2, padding: '0.5rem 0.75rem', fontSize: '0.85rem', color: TEXT }}>
                {reply ? (
                  <div className="prose-chat">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{reply}</ReactMarkdown>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: MUTED }}>
                    <Loader2 className="h-4 w-4 animate-spin" /> Dispatching to procurement-manager…
                  </div>
                )}
                <div ref={replyRef} />
              </div>
            </div>
          )}

          {proxyError && (
            <div className="sd-alert-row critical">
              {proxyError}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', borderTop: `1px solid ${BORDER}`, paddingTop: '0.75rem', marginTop: '0.75rem' }}>
          <button type="button" onClick={onClose} className="sd-btn sd-btn-secondary">
            Close
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={sending || !instruction.trim()}
            className="sd-btn sd-btn-primary"
          >
            {sending ? 'Dispatching…' : 'Confirm & Dispatch'}
          </button>
        </div>
      </div>
    </button>
  );
}
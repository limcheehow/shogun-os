import { LineChart } from '../charts';
import { chartColors } from '../../../lib/palette';
import type { CeoDashboardStats, ChatInboxRow } from '../../../lib/types';

// Phase-1 mock-driven tab. Reads only from the CeoDashboardStats contract so
// swapping mock→live (Phase 2) touches dashboard.py, not this file.

interface Props { stats: CeoDashboardStats; color: string }

const MUTED = 'var(--samurai-muted)';
const TEXT = 'var(--samurai-text)';
const BORDER = 'var(--samurai-border)';

const th = { fontSize: '0.72rem', fontWeight: 500, color: MUTED } as const;
function Th({ children, align }: { children: React.ReactNode; align: 'left' | 'right' | 'center' }) {
  return <th className="px-3 py-2.5" style={{ ...th, textAlign: align }}>{children}</th>;
}

const PLATFORM_CHIP: Record<ChatInboxRow['platform'], string> = {
  Shopee: 'muted',
  Lazada: 'muted',
  'FB Messenger': 'muted',
  WhatsApp: 'muted',
};

const STATUS_CHIP: Record<ChatInboxRow['status'], string> = {
  'AI Handling': 'muted',
  'Escalated to Human': 'warn',
  Resolved: 'ok',
};

export function OmnichannelChatTab({ stats, color }: Props) {
  const channels = stats.channelVolume;
  const totalMessages = channels.shopee + channels.lazada + channels.fbMessenger + channels.whatsapp;

  const volumeCards = [
    { label: 'Shopee Messages', value: channels.shopee, accent: 'ok' as const },
    { label: 'Lazada Messages', value: channels.lazada, accent: 'muted' as const },
    { label: 'FB Messenger', value: channels.fbMessenger, accent: 'muted' as const },
    { label: 'WhatsApp Messages', value: channels.whatsapp, accent: 'muted' as const },
  ];

  const slaCards = [
    {
      label: 'Avg Response Time',
      value: `${stats.avgResponseMinutes.toFixed(1)} min`,
      badge: stats.avgResponseMinutes >= 15 ? { label: 'Over SLA', cls: 'bad' } : { label: 'Within SLA', cls: 'ok' },
    },
    { label: 'SLA Compliance', value: `${stats.slaCompliancePct.toFixed(1)}%`, badge: { label: 'Target < 15m', cls: 'muted' } },
    { label: 'AI Resolution Rate', value: `${stats.aiResolutionPct.toFixed(1)}%`, badge: { label: 'Auto-resolved', cls: 'muted' } },
    { label: 'Chat-to-Order Conversion', value: `${stats.chatToOrderPct.toFixed(1)}%`, badge: { label: 'Weekly trend', cls: 'muted' } },
  ];

  const trendKeys = ['shopee', 'lazada', 'fbMessenger', 'whatsapp'];
  const trendLabels = { shopee: 'Shopee', lazada: 'Lazada', fbMessenger: 'FB Messenger', whatsapp: 'WhatsApp' };
  const trendColors = chartColors(color, 4);

  return (
    <div className="sd-stack">
      {/* Channel Volume Cards (spec §2.3) */}
      <div className="sd-kpi-grid">
        {volumeCards.map((c) => (
          <div key={c.label} className="sd-kpi-card">
            <div className="sd-kpi-label">{c.label}</div>
            <div className="sd-kpi-value">{c.value.toLocaleString()}</div>
            <div className="sd-kpi-sub" style={{ fontSize: '0.72rem', color: MUTED }}>
              {totalMessages > 0 ? ((c.value / totalMessages) * 100).toFixed(0) : 0}% of volume
            </div>
          </div>
        ))}
      </div>

      {/* Response SLA Metric Cards (spec §2.3) */}
      <div className="sd-kpi-grid">
        {slaCards.map((c) => (
          <div key={c.label} className="sd-kpi-card">
            <div className="sd-kpi-label">{c.label}</div>
            <div className="sd-kpi-value">{c.value}</div>
            {c.badge && (
              <span className={`sd-chip ${c.badge.cls}`} style={{ marginTop: '0.4rem' }}>{c.badge.label}</span>
            )}
          </div>
        ))}
      </div>

      {/* Chat-to-Order Conversion Trend (spec §2.3) */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Chat-to-Order Conversion Trend</h3>
        <p className="sd-chart-sub">Weekly conversion percentage across all four channels</p>
        <LineChart
          data={stats.chatToOrderTrend}
          xKey="week"
          yKey="shopee"
          color={color}
          unit=""
          height={240}
          dataKeys={trendKeys}
          colors={trendColors}
          labels={trendLabels}
        />
      </div>

      {/* Live Multi-Platform Inbox & Escalation Table (spec §2.3) */}
      <div className="sd-chart-card">
        <h3 className="sd-chart-title">Live Multi-Platform Inbox & Escalation Log</h3>
        <p className="sd-chart-sub">Real-time customer conversations across Shopee, Lazada, FB Messenger & WhatsApp</p>
        {stats.chatInbox.length === 0 ? (
          <p style={{ color: MUTED, padding: '1rem 0', textAlign: 'center' }}>No active conversations.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <Th align="left">Customer</Th>
                  <Th align="left">Platform</Th>
                  <Th align="left">Last Message</Th>
                  <Th align="right">SLA Timer</Th>
                  <Th align="center">Status</Th>
                </tr>
              </thead>
              <tbody>
                {stats.chatInbox.map((row, i) => {
                  const overSla = row.responseMinutes > 15;
                  return (
                    <tr key={i} style={{ borderBottom: `1px solid ${BORDER}` }}>
                      <td className="px-3 py-2.5" style={{ fontWeight: 500, color: TEXT }}>{row.customer}</td>
                      <td className="px-3 py-2.5">
                        <span className={`sd-chip ${PLATFORM_CHIP[row.platform]}`}>{row.platform}</span>
                      </td>
                      <td className="px-3 py-2.5" style={{ color: MUTED, maxWidth: '24rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {row.lastMessage}
                      </td>
                      <td className="px-3 py-2.5 text-right" style={{ fontWeight: 600, color: overSla ? 'var(--samurai-danger)' : TEXT }}>
                        {row.responseMinutes} min{overSla ? ' ⚠' : ''}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`sd-chip ${STATUS_CHIP[row.status]}`}>{row.status}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Platform legend swatches for the trend chart */}
      <div className="sd-card" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {trendKeys.map((k, i) => (
          <div key={k} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.72rem', color: MUTED }}>
            <span style={{ display: 'inline-block', width: '0.6rem', height: '0.6rem', borderRadius: '999px', background: trendColors[i] }} />
            {trendLabels[k as keyof typeof trendLabels]}
          </div>
        ))}
      </div>
    </div>
  );
}

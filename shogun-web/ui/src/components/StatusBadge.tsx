import clsx from 'clsx';
import type { StatusLevel } from '../lib/types';

const LABELS: Record<StatusLevel, string> = {
  online: 'Online',
  degraded: 'Degraded',
  offline: 'Offline',
  unknown: 'Unknown',
  pending: 'Pending',
};

const COLORS: Record<StatusLevel, string> = {
  online: 'bg-emerald-500',
  degraded: 'bg-amber-400',
  offline: 'bg-rose-500',
  unknown: 'bg-slate-400',
  pending: 'bg-sky-400',
};

interface StatusBadgeProps {
  status?: StatusLevel | string | null;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
  showLabel?: boolean;
}

function normalize(status?: StatusLevel | string | null): StatusLevel {
  if (!status) return 'unknown';
  const s = String(status).toLowerCase();
  if (s === 'online' || s === 'healthy' || s === 'ok' || s === 'active') return 'online';
  if (s === 'degraded' || s === 'warning' || s === 'partial') return 'degraded';
  if (s === 'offline' || s === 'down' || s === 'error' || s === 'failed') return 'offline';
  if (s === 'pending' || s === 'starting' || s === 'connecting') return 'pending';
  return 'unknown';
}

export default function StatusBadge({
  status,
  label,
  size = 'sm',
  className,
  showLabel = true,
}: StatusBadgeProps) {
  const level = normalize(status);
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-medium text-slate-600',
        size === 'sm' ? 'text-xs' : 'text-sm',
        className,
      )}
    >
      <span
        className={clsx(
          'rounded-full',
          COLORS[level],
          size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2',
        )}
      />
      {showLabel && <span>{label || LABELS[level]}</span>}
    </span>
  );
}

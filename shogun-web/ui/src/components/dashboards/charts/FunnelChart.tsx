import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import { chartColors } from '../../../lib/palette';
import type { FunnelEntry } from '../../../lib/types';

interface FunnelChartProps {
  data: FunnelEntry[];
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  valueKey?: 'value' | 'count';
}

export function FunnelChart({
  data, color = '#6366f1', colors, unit = '', height = 280, valueKey = 'value',
}: FunnelChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
        No data
      </div>
    );
  }

  const palette = colors || chartColors(color, data.length);
  const formatter = (value: unknown) =>
    [unit ? `${unit}${Number(value ?? 0).toLocaleString()}` : Number(value ?? 0).toLocaleString()] as [string];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data={data as any}
        layout="vertical"
        margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => (unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString())}
        />
        <YAxis type="category" dataKey="stage" tick={{ fontSize: 11, fill: '#64748b' }}
          axisLine={false} tickLine={false} width={100}
        />
        <Tooltip formatter={formatter as never} contentStyle={{
          background: '#fff', border: '1px solid #e2e8f0',
          borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }} />
        <Bar dataKey={valueKey} radius={[0, 4, 4, 0]} maxBarSize={36}>
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]}
              fillOpacity={1 - (i * 0.08)}
            />
          ))}
        </Bar>
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
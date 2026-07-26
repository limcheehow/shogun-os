import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { chartColors } from '../../../lib/palette';

interface BarChartProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  xKey: string;
  yKey: string;
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  stacked?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onClick?: (entry: any) => void;
  dataKeys?: string[];
}

export function BarChart({
  data, xKey, yKey, color = '#6366f1', colors, unit = '',
  height = 250, stacked = false, onClick, dataKeys,
}: BarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
        No data
      </div>
    );
  }

  const palette = colors || chartColors(color, dataKeys?.length || 1);
  const formatter = (value: unknown) =>
    [unit ? `${unit}${Number(value ?? 0).toLocaleString()}` : Number(value ?? 0).toLocaleString()] as [string];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart
        data={data}
        margin={{ top: 5, right: 5, left: -10, bottom: 5 }}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onClick={(e: any) => {
          if (e?.activePayload?.[0]?.payload) onClick?.(e.activePayload[0].payload);
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => (unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString())}
        />
        <Tooltip formatter={formatter as never} contentStyle={{
          background: '#fff', border: '1px solid #e2e8f0',
          borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }} />
        {dataKeys && dataKeys.length > 0
          ? dataKeys.map((k, i) => (
              <Bar
                key={k} dataKey={k} fill={palette[i % palette.length]}
                stackId={stacked ? 'stack' : undefined}
                radius={[3, 3, 0, 0]}
              />
            ))
          : <Bar dataKey={yKey} fill={palette[0]} radius={[3, 3, 0, 0]} />
        }
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
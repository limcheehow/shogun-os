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
import { ChartEmpty, CHART_TICK, CHART_TICK_SMALL, CHART_TOOLTIP_STYLE } from './empty';
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
    return <ChartEmpty />;
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
        <CartesianGrid strokeDasharray="3 3" stroke="var(--samurai-border)" horizontal={false} />
        <XAxis type="number" tick={CHART_TICK} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => (unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString())}
        />
        <YAxis type="category" dataKey="stage" tick={CHART_TICK_SMALL}
          axisLine={false} tickLine={false} width={100}
        />
        <Tooltip formatter={formatter as never} contentStyle={CHART_TOOLTIP_STYLE} />
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
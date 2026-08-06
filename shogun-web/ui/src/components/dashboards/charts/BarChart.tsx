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
import { ChartEmpty, CHART_TICK, CHART_TICK_SMALL, CHART_TOOLTIP_STYLE } from './empty';

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
  interval?: number | 'preserveStart' | 'preserveEnd' | 'preserveStartEnd';
}

export function BarChart({
  data, xKey, yKey, color = '#6366f1', colors, unit = '',
  height = 250, stacked = false, onClick, dataKeys, interval = 0,
}: BarChartProps) {
  if (!data || data.length === 0) {
    return <ChartEmpty />;
  }

  const palette = colors || chartColors(color, dataKeys?.length || 1);
  const formatter = (value: unknown) =>
    [unit ? `${unit}${Number(value ?? 0).toLocaleString()}` : Number(value ?? 0).toLocaleString()] as [string];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart
        data={data}
        margin={{ top: 5, right: 5, left: -10, bottom: 15 }}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onClick={(e: any) => {
          if (e?.activePayload?.[0]?.payload) onClick?.(e.activePayload[0].payload);
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--samurai-border)" />
        <XAxis dataKey={xKey} interval={interval} tick={CHART_TICK_SMALL} axisLine={false} tickLine={false} />
        <YAxis
          tick={CHART_TICK} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => (unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString())}
        />
        <Tooltip formatter={formatter as never} contentStyle={CHART_TOOLTIP_STYLE} />
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
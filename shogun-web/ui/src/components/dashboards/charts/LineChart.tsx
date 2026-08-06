import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { chartColors } from '../../../lib/palette';
import { ChartEmpty, CHART_TICK, CHART_TOOLTIP_STYLE } from './empty';

interface LineChartProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  xKey: string;
  yKey: string;
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  dataKeys?: string[];
  labels?: Record<string, string>;
}

export function LineChart({
  data, xKey, yKey, color = '#6366f1', colors, unit = '', height = 250, dataKeys, labels,
}: LineChartProps) {
  if (!data || data.length === 0) {
    return <ChartEmpty />;
  }

  const palette = colors || chartColors(color, dataKeys?.length || 1);
  const formatter = (value: unknown) =>
    [unit ? `${unit}${Number(value ?? 0).toLocaleString()}` : Number(value ?? 0).toLocaleString()] as [string];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--samurai-border)" />
        <XAxis dataKey={xKey} tick={CHART_TICK} axisLine={false} tickLine={false} />
        <YAxis
          tick={CHART_TICK} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => (unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString())}
        />
        <Tooltip formatter={formatter as never} contentStyle={CHART_TOOLTIP_STYLE} />
        {dataKeys && dataKeys.length > 0 && (
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
        )}
        {dataKeys && dataKeys.length > 0
          ? dataKeys.map((k, i) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                name={labels?.[k] || k}
                stroke={palette[i % palette.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
            ))
          : <Line type="monotone" dataKey={yKey} name={labels?.[yKey] || yKey} stroke={palette[0]} strokeWidth={2} dot={{ r: 3 }} />
        }
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}
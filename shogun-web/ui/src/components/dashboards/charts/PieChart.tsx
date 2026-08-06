import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { chartColors } from '../../../lib/palette';
import { ChartEmpty, CHART_TOOLTIP_STYLE } from './empty';

interface PieChartProps {
  data: { name: string; value: number }[];
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  innerRadius?: number;
  showLegend?: boolean;
}

export function PieChart({
  data, color = '#6366f1', colors, unit = '', height = 250,
  innerRadius = 50, showLegend = true,
}: PieChartProps) {
  if (!data || data.length === 0) {
    return <ChartEmpty />;
  }

  const palette = colors || chartColors(color, data.length);
  const formatter = (value: unknown) =>
    [unit ? `${unit}${Number(value ?? 0).toLocaleString()}` : Number(value ?? 0).toLocaleString()] as [string];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPieChart>
        <Pie
          data={data} cx="50%" cy="50%" innerRadius={innerRadius} outerRadius={80}
          dataKey="value" paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]} />
          ))}
        </Pie>
        <Tooltip formatter={formatter as never} contentStyle={CHART_TOOLTIP_STYLE} />
        {showLegend && (
          <Legend
            formatter={(value: string) => {
              const item = data.find((d) => d.name === value);
              if (!item) return value;
              const formattedVal = unit ? `${unit}${Number(item.value).toLocaleString()}` : Number(item.value).toLocaleString();
              return `${value} (${formattedVal})`;
            }}
          />
        )}
      </RechartsPieChart>
    </ResponsiveContainer>
  );
}
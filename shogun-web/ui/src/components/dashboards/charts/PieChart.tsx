import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { chartColors } from '../../../lib/palette';

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
      <RechartsPieChart>
        <Pie
          data={data} cx="50%" cy="50%" innerRadius={innerRadius} outerRadius={80}
          dataKey="value" paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]} />
          ))}
        </Pie>
        <Tooltip formatter={formatter as never} contentStyle={{
          background: '#fff', border: '1px solid #e2e8f0',
          borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }} />
        {showLegend && <Legend />}
      </RechartsPieChart>
    </ResponsiveContainer>
  );
}
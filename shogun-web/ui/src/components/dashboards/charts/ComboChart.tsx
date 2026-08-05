import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';

interface ComboSeries {
  key: string;
  label: string;
  type: 'bar' | 'line';
  color: string;
}

interface ComboChartProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  xKey: string;
  series: ComboSeries[];
  unit?: string;
  height?: number;
}

export function ComboChart({ data, xKey, series, unit = '', height = 250 }: ComboChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
        No data
      </div>
    );
  }

  const fmt = (v: unknown) =>
    [unit ? `${unit}${Number(v ?? 0).toLocaleString()}` : Number(v ?? 0).toLocaleString()] as [string];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => (unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString())}
        />
        <Tooltip
          formatter={fmt as never}
          contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}
        />
        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
        {series.map((s) =>
          s.type === 'bar' ? (
            <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[3, 3, 0, 0]} />
          ) : (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} dot={{ r: 3 }} connectNulls />
          ),
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

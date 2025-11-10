import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Metrics } from '../../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

interface FeedbackBreakdownChartProps {
  metrics: Metrics;
}

const COLORS = {
  helpful: 'hsl(142, 71%, 45%)',
  not_helpful: 'hsl(var(--destructive))',
  needs_improvement: 'hsl(var(--primary))',
};

export function FeedbackBreakdownChart({ metrics }: FeedbackBreakdownChartProps) {
  const total = metrics.total_feedback;
  const data = [
    {
      name: 'Helpful',
      value: metrics.helpful_feedback,
      percentage: total > 0 ? ((metrics.helpful_feedback / total) * 100).toFixed(1) : '0',
      color: COLORS.helpful,
    },
    {
      name: 'Not Helpful',
      value: metrics.not_helpful_feedback,
      percentage: total > 0 ? ((metrics.not_helpful_feedback / total) * 100).toFixed(1) : '0',
      color: COLORS.not_helpful,
    },
    {
      name: 'Needs Improvement',
      value: metrics.total_feedback - metrics.helpful_feedback - metrics.not_helpful_feedback,
      percentage: total > 0 ? (((metrics.total_feedback - metrics.helpful_feedback - metrics.not_helpful_feedback) / total) * 100).toFixed(1) : '0',
      color: COLORS.needs_improvement,
    },
  ].filter(item => item.value > 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="rounded-md border bg-card p-2 shadow-sm">
          <p className="text-sm font-medium">{data.name}</p>
          <p className="text-xs text-muted-foreground">
            Count: {data.value} ({data.percentage}%)
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Feedback Breakdown</CardTitle>
        <CardDescription>Distribution of agent feedback ratings</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              type="number"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
            />
            <YAxis 
              type="category" 
              dataKey="name"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              width={120}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="value" 
              radius={[0, 4, 4, 0]}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}


import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Metrics } from '../../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

interface StatusDistributionChartProps {
  metrics: Metrics;
}

const COLORS = {
  active: 'hsl(var(--primary))',
  resolved: 'hsl(142, 71%, 45%)',
  escalated: 'hsl(var(--destructive))',
};

export function StatusDistributionChart({ metrics }: StatusDistributionChartProps) {
  const data = [
    { name: 'Active', value: metrics.active_conversations, color: COLORS.active },
    { name: 'Resolved', value: metrics.resolved_conversations, color: COLORS.resolved },
    { name: 'Escalated', value: metrics.escalated_conversations, color: COLORS.escalated },
  ].filter(item => item.value > 0);

  const total = data.reduce((sum, item) => sum + item.value, 0);

  const renderLabel = (entry: any) => {
    const percent = ((entry.value / total) * 100).toFixed(1);
    return `${entry.name}: ${percent}%`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conversation Status</CardTitle>
        <CardDescription>Distribution of conversation statuses</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderLabel}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: 'calc(var(--radius) - 2px)',
              }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}


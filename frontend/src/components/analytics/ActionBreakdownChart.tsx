import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { AgentPerformance } from '../../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

interface ActionBreakdownChartProps {
  agentPerformance: AgentPerformance;
}

const COLORS = {
  approve: 'hsl(142, 71%, 45%)',
  reject: 'hsl(var(--destructive))',
  edit: 'hsl(var(--primary))',
  escalate: 'hsl(24, 95%, 53%)',
  default: 'hsl(var(--muted))',
};

export function ActionBreakdownChart({ agentPerformance }: ActionBreakdownChartProps) {
  const actionBreakdown = agentPerformance.action_breakdown || {};
  
  const data = Object.entries(actionBreakdown)
    .map(([action, count]) => ({
      name: action.charAt(0).toUpperCase() + action.slice(1),
      value: count,
      percentage: agentPerformance.total_actions > 0 
        ? ((count / agentPerformance.total_actions) * 100).toFixed(1) 
        : '0',
      color: COLORS[action as keyof typeof COLORS] || COLORS.default,
    }))
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value);

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

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Action Breakdown</CardTitle>
          <CardDescription>Distribution of agent actions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            No action data available
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Action Breakdown</CardTitle>
        <CardDescription>Distribution of agent actions on AI responses</CardDescription>
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
              width={100}
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


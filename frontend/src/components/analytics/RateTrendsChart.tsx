import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { DailyMetrics } from '../../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

interface RateTrendsChartProps {
  data: DailyMetrics[];
}

export function RateTrendsChart({ data }: RateTrendsChartProps) {
  const chartData = data.map((item) => {
    const total = item.total_conversations;
    const resolutionRate = total > 0 ? (item.resolved_conversations / total) * 100 : 0;
    const escalationRate = total > 0 ? (item.escalated_conversations / total) * 100 : 0;
    
    return {
      date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      resolutionRate: Number(resolutionRate.toFixed(1)),
      escalationRate: Number(escalationRate.toFixed(1)),
    };
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Resolution & Escalation Rates</CardTitle>
        <CardDescription>Trend of AI effectiveness over time</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorResolution" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorEscalation" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="date" 
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
            />
            <YAxis 
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              label={{ value: 'Rate (%)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: 'calc(var(--radius) - 2px)',
              }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
            />
            <Legend />
            <Area 
              type="monotone" 
              dataKey="resolutionRate" 
              stackId="1"
              stroke="hsl(142, 71%, 45%)" 
              fill="url(#colorResolution)"
              name="Resolution Rate (%)"
            />
            <Area 
              type="monotone" 
              dataKey="escalationRate" 
              stackId="2"
              stroke="hsl(var(--destructive))" 
              fill="url(#colorEscalation)"
              name="Escalation Rate (%)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}


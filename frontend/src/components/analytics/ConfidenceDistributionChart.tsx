import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { DailyMetrics } from '../../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

interface ConfidenceDistributionChartProps {
  data: DailyMetrics[];
}

export function ConfidenceDistributionChart({ data }: ConfidenceDistributionChartProps) {
  // Calculate distribution of confidence scores into bins
  const bins = {
    '0-50%': 0,
    '50-70%': 0,
    '70-85%': 0,
    '85-100%': 0,
  };

  data.forEach((item) => {
    const score = item.avg_confidence_score * 100;
    if (score < 50) {
      bins['0-50%']++;
    } else if (score < 70) {
      bins['50-70%']++;
    } else if (score < 85) {
      bins['70-85%']++;
    } else {
      bins['85-100%']++;
    }
  });

  const chartData = Object.entries(bins).map(([range, count]) => ({
    range,
    count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Confidence Score Distribution</CardTitle>
        <CardDescription>Distribution of AI confidence scores by range</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="range" 
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
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: 'calc(var(--radius) - 2px)',
              }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
            />
            <Bar 
              dataKey="count" 
              fill="hsl(var(--primary))"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}


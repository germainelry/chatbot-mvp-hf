/**
 * Analytics Dashboard
 * Production-ready analytics dashboard with comprehensive visualizations
 * and meaningful metrics for AI customer support system.
 */
import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  MessageSquare, 
  CheckCircle, 
  AlertTriangle, 
  ThumbsUp, 
  BarChart2, 
  Loader2,
  Activity,
  Target,
  Zap,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import { 
  getMetrics, 
  getFeedbackHistory, 
  getTimeSeriesMetrics,
  Metrics, 
  FeedbackHistory,
  TimeSeriesResponse
} from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { PageHeader } from '../components/layout/PageHeader';
import { cn } from '../components/ui/utils';
import { ConversationTrendsChart } from '../components/analytics/ConversationTrendsChart';
import { StatusDistributionChart } from '../components/analytics/StatusDistributionChart';
import { ConfidenceDistributionChart } from '../components/analytics/ConfidenceDistributionChart';
import { FeedbackBreakdownChart } from '../components/analytics/FeedbackBreakdownChart';
import { RateTrendsChart } from '../components/analytics/RateTrendsChart';

export default function Analytics() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [feedbackHistory, setFeedbackHistory] = useState<FeedbackHistory[]>([]);
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [metricsData, feedbackData, timeSeries] = await Promise.all([
        getMetrics(),
        getFeedbackHistory(),
        getTimeSeriesMetrics(30),
      ]);
      setMetrics(metricsData);
      setFeedbackHistory(feedbackData);
      setTimeSeriesData(timeSeries);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !metrics) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
          <p className="text-muted-foreground">Loading analytics...</p>
        </div>
      </div>
    );
  }

  const MetricCard = ({
    title,
    value,
    icon: Icon,
    iconBg,
    subtitle,
    trend,
    trendValue,
  }: {
    title: string;
    value: string | number;
    icon: any;
    iconBg: string;
    subtitle?: string;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
  }) => {
    const TrendIcon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : null;
    const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-muted-foreground';

    return (
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2 gap-3">
          <CardTitle className="text-sm font-medium text-muted-foreground min-w-0 flex-1 truncate">
            {title}
          </CardTitle>
          <div className={cn("p-2 rounded-md shrink-0", iconBg)}>
            <Icon className="h-4 w-4 text-white" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{value}</div>
          {subtitle && (
            <div className="flex items-center gap-1 mt-1">
              {trend && TrendIcon && (
                <TrendIcon className={cn("h-3 w-3", trendColor)} />
              )}
              <p className="text-xs text-muted-foreground">
                {trendValue ? `${trendValue} ` : ''}{subtitle}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const getRatingBadgeVariant = (rating: string) => {
    switch (rating) {
      case 'helpful':
        return 'default';
      case 'not_helpful':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  // Calculate deflection rate (inverse of escalation rate)
  const deflectionRate = 100 - metrics.escalation_rate;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics Dashboard"
        description="Comprehensive insights into your AI support system performance"
      />

      {/* Key Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          title="Total Conversations"
          value={metrics.total_conversations}
          icon={MessageSquare}
          iconBg="bg-primary"
          subtitle="All time"
        />
        
        <MetricCard
          title="Active Conversations"
          value={metrics.active_conversations}
          icon={Activity}
          iconBg="bg-blue-500"
          subtitle="Currently active"
        />
        
        <MetricCard
          title="Resolution Rate"
          value={`${metrics.resolution_rate.toFixed(1)}%`}
          icon={CheckCircle}
          iconBg="bg-green-500"
          subtitle={`${metrics.resolved_conversations} resolved`}
          trend="up"
        />
        
        <MetricCard
          title="Deflection Rate"
          value={`${deflectionRate.toFixed(1)}%`}
          icon={Target}
          iconBg="bg-emerald-500"
          subtitle={`${Math.round(metrics.total_conversations * deflectionRate / 100)} handled by AI`}
          trend="up"
        />
        
        <MetricCard
          title="Escalation Rate"
          value={`${metrics.escalation_rate.toFixed(1)}%`}
          icon={AlertTriangle}
          iconBg="bg-red-500"
          subtitle={`${metrics.escalated_conversations} escalated`}
          trend="down"
        />
        
        <MetricCard
          title="Avg Confidence"
          value={`${(metrics.avg_confidence_score * 100).toFixed(0)}%`}
          icon={Zap}
          iconBg="bg-purple-500"
          subtitle="AI response confidence"
        />
      </div>

      {/* Visualization Section */}
      {timeSeriesData && (
        <div className="grid gap-6 md:grid-cols-2">
          <ConversationTrendsChart data={timeSeriesData.metrics} />
          <StatusDistributionChart metrics={metrics} />
        </div>
      )}

      {timeSeriesData && (
        <div className="grid gap-6 md:grid-cols-2">
          <RateTrendsChart data={timeSeriesData.metrics} />
          <ConfidenceDistributionChart data={timeSeriesData.metrics} />
        </div>
      )}

      <FeedbackBreakdownChart metrics={metrics} />

      {/* Key Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart2 className="h-5 w-5" />
            Key Insights
          </CardTitle>
          <CardDescription>
            Automated analysis of your support metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
              <div className="p-2 rounded-md bg-green-100 dark:bg-green-900/20">
                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-sm mb-1">AI Performance</h4>
                <p className="text-xs text-muted-foreground">
                  {deflectionRate.toFixed(1)}% of conversations handled without escalation
                </p>
              </div>
            </div>

            {metrics.avg_confidence_score < 0.7 ? (
              <div className="flex items-start gap-3 p-4 rounded-lg border bg-card border-yellow-200 dark:border-yellow-800">
                <div className="p-2 rounded-md bg-yellow-100 dark:bg-yellow-900/20">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-sm mb-1">Confidence Opportunity</h4>
                  <p className="text-xs text-muted-foreground">
                    Average confidence is {(metrics.avg_confidence_score * 100).toFixed(0)}%. Consider expanding knowledge base.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
                <div className="p-2 rounded-md bg-blue-100 dark:bg-blue-900/20">
                  <Zap className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-sm mb-1">Strong Confidence</h4>
                  <p className="text-xs text-muted-foreground">
                    Average confidence is {(metrics.avg_confidence_score * 100).toFixed(0)}% - excellent AI performance
                  </p>
                </div>
              </div>
            )}

            <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
              <div className="p-2 rounded-md bg-purple-100 dark:bg-purple-900/20">
                <ThumbsUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-sm mb-1">Feedback Collection</h4>
                <p className="text-xs text-muted-foreground">
                  {metrics.feedback_sentiment.toFixed(1)}% positive feedback rate from {metrics.total_feedback} responses
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Feedback */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Agent Feedback</CardTitle>
          <CardDescription>
            Latest feedback from support agents for model improvement
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Conversation ID</TableHead>
                  <TableHead>Rating</TableHead>
                  <TableHead>Agent Notes</TableHead>
                  <TableHead>Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {feedbackHistory.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                      No feedback collected yet
                    </TableCell>
                  </TableRow>
                ) : (
                  feedbackHistory.map((feedback) => (
                    <TableRow key={feedback.id}>
                      <TableCell className="font-medium">
                        #{feedback.conversation_id}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getRatingBadgeVariant(feedback.rating)}>
                          {feedback.rating.replace('_', ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-md">
                        <p className="truncate text-sm">
                          {feedback.notes || feedback.agent_correction || 'No notes provided'}
                        </p>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(feedback.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

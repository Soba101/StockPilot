'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { CalendarIcon, Download, TrendingUp, TrendingDown, AlertTriangle, FileText, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

interface WeekInReviewReport {
  report_id: string;
  generated_at: string;
  period: {
    period_start: string;
    period_end: string;
    total_revenue: number;
    total_units: number;
    total_orders: number;
    avg_order_value: number;
    gross_margin: number;
    margin_percent: number;
    revenue_change_percent: number;
    units_change_percent: number;
  };
  top_products: Array<{
    name: string;
    sku: string;
    category: string;
    revenue: number;
    units: number;
    margin_percent: number;
    rank: number;
  }>;
  inventory_alerts: Array<{
    product_name: string;
    sku: string;
    location_name: string;
    current_stock: number;
    reorder_point: number;
    alert_type: string;
  }>;
  channel_insights: Array<{
    channel: string;
    revenue: number;
    units: number;
    orders: number;
    market_share_percent: number;
  }>;
  key_insights: string[];
  recommendations: string[];
  summary: {
    performance_score: number;
    health_indicators: {
      revenue_trend: string;
      inventory_health: string;
      channel_diversity: string;
    };
  };
}

export default function ReportsPage() {
  const [selectedStartDate, setSelectedStartDate] = useState<Date>();
  const [selectedEndDate, setSelectedEndDate] = useState<Date>();
  const [isStartCalendarOpen, setIsStartCalendarOpen] = useState(false);
  const [isEndCalendarOpen, setIsEndCalendarOpen] = useState(false);

  // Query for the Week in Review report
  const { data: report, isLoading, error } = useQuery<WeekInReviewReport>({
    queryKey: ['week-in-review', selectedStartDate, selectedEndDate],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedStartDate) params.append('start_date', format(selectedStartDate, 'yyyy-MM-dd'));
      if (selectedEndDate) params.append('end_date', format(selectedEndDate, 'yyyy-MM-dd'));
      
      const response = await api.get(`/reports/week-in-review?${params.toString()}`);
      return response.data;
    },
  });

  const handleExportCSV = async () => {
    const params = new URLSearchParams();
    if (selectedStartDate) params.append('start_date', format(selectedStartDate, 'yyyy-MM-dd'));
    if (selectedEndDate) params.append('end_date', format(selectedEndDate, 'yyyy-MM-dd'));
    
    const response = await api.get(`/reports/week-in-review/export/csv?${params.toString()}`, {
      responseType: 'blob',
    });
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `week-in-review-${format(new Date(), 'yyyy-MM-dd')}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleExportJSON = async () => {
    const params = new URLSearchParams();
    if (selectedStartDate) params.append('start_date', format(selectedStartDate, 'yyyy-MM-dd'));
    if (selectedEndDate) params.append('end_date', format(selectedEndDate, 'yyyy-MM-dd'));
    
    const response = await api.get(`/reports/week-in-review/export/json?${params.toString()}`, {
      responseType: 'blob',
    });
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `week-in-review-${format(new Date(), 'yyyy-MM-dd')}.json`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const getHealthBadgeColor = (health: string) => {
    switch (health) {
      case 'good': return 'bg-green-500';
      case 'needs_attention': return 'bg-yellow-500';
      case 'poor': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getTrendIcon = (change: number) => {
    if (change > 0) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (change < 0) return <TrendingDown className="h-4 w-4 text-red-500" />;
    return <div className="h-4 w-4" />;
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">Generating report...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-red-500">
              Error loading report: {error instanceof Error ? error.message : 'Unknown error'}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Reports</h1>
          <p className="text-muted-foreground">Weekly business insights and analytics</p>
        </div>
        <div className="flex items-center gap-4">
          {/* Date Range Selector */}
          <div className="flex items-center gap-2">
            <Popover open={isStartCalendarOpen} onOpenChange={setIsStartCalendarOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn("justify-start text-left font-normal", !selectedStartDate && "text-muted-foreground")}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {selectedStartDate ? format(selectedStartDate, "PPP") : "Start date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={selectedStartDate}
                  onSelect={setSelectedStartDate}
                  initialFocus
                />
              </PopoverContent>
            </Popover>

            <Popover open={isEndCalendarOpen} onOpenChange={setIsEndCalendarOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn("justify-start text-left font-normal", !selectedEndDate && "text-muted-foreground")}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {selectedEndDate ? format(selectedEndDate, "PPP") : "End date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={selectedEndDate}
                  onSelect={setSelectedEndDate}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          {/* Export Buttons */}
          <Button onClick={handleExportCSV} variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
          <Button onClick={handleExportJSON} variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export JSON
          </Button>
        </div>
      </div>

      {report && (
        <>
          {/* Report Header */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Week in Review Report
                <Badge variant="outline">{report.report_id}</Badge>
              </CardTitle>
              <div className="text-sm text-muted-foreground">
                Period: {format(new Date(report.period.period_start), 'MMM dd')} - {format(new Date(report.period.period_end), 'MMM dd, yyyy')}
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{report.summary.performance_score}</div>
                  <div className="text-sm text-muted-foreground">Performance Score</div>
                </div>
                <div className="text-center">
                  <Badge className={getHealthBadgeColor(report.summary.health_indicators.revenue_trend)}>
                    {report.summary.health_indicators.revenue_trend}
                  </Badge>
                  <div className="text-sm text-muted-foreground mt-1">Revenue Trend</div>
                </div>
                <div className="text-center">
                  <Badge className={getHealthBadgeColor(report.summary.health_indicators.inventory_health)}>
                    {report.summary.health_indicators.inventory_health}
                  </Badge>
                  <div className="text-sm text-muted-foreground mt-1">Inventory Health</div>
                </div>
                <div className="text-center">
                  <Badge className={getHealthBadgeColor(report.summary.health_indicators.channel_diversity)}>
                    {report.summary.health_indicators.channel_diversity}
                  </Badge>
                  <div className="text-sm text-muted-foreground mt-1">Channel Diversity</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
                {getTrendIcon(report.period.revenue_change_percent)}
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${report.period.total_revenue.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  {report.period.revenue_change_percent > 0 ? '+' : ''}{report.period.revenue_change_percent.toFixed(1)}% from last week
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Units Sold</CardTitle>
                {getTrendIcon(report.period.units_change_percent)}
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{report.period.total_units.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  {report.period.units_change_percent > 0 ? '+' : ''}{report.period.units_change_percent.toFixed(1)}% from last week
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Orders</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{report.period.total_orders.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  Avg order value: ${report.period.avg_order_value.toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Gross Margin</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{report.period.margin_percent.toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground">
                  ${report.period.gross_margin.toLocaleString()} total margin
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Tabs */}
          <Tabs defaultValue="insights" className="space-y-4">
            <TabsList>
              <TabsTrigger value="insights">Insights & Recommendations</TabsTrigger>
              <TabsTrigger value="products">Top Products</TabsTrigger>
              <TabsTrigger value="inventory">Inventory Alerts</TabsTrigger>
              <TabsTrigger value="channels">Channel Performance</TabsTrigger>
            </TabsList>

            <TabsContent value="insights" className="space-y-4">
              <div className="grid md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5" />
                      Key Insights
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {report.key_insights.map((insight, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                          <span className="text-sm">{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5" />
                      Recommendations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {report.recommendations.map((recommendation, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                          <span className="text-sm">{recommendation}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="products">
              <Card>
                <CardHeader>
                  <CardTitle>Top Performing Products</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {report.top_products.map((product) => (
                      <div key={product.sku} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center gap-4">
                          <Badge variant="outline">#{product.rank}</Badge>
                          <div>
                            <div className="font-medium">{product.name}</div>
                            <div className="text-sm text-muted-foreground">{product.sku} • {product.category}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold">${product.revenue.toLocaleString()}</div>
                          <div className="text-sm text-muted-foreground">
                            {product.units} units • {product.margin_percent.toFixed(1)}% margin
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="inventory">
              <Card>
                <CardHeader>
                  <CardTitle>Inventory Alerts</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {report.inventory_alerts.length > 0 ? (
                      report.inventory_alerts.map((alert, index) => (
                        <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex items-center gap-4">
                            <Badge 
                              variant={alert.alert_type === 'out_of_stock' ? 'destructive' : 'secondary'}
                            >
                              {alert.alert_type.replace('_', ' ')}
                            </Badge>
                            <div>
                              <div className="font-medium">{alert.product_name}</div>
                              <div className="text-sm text-muted-foreground">{alert.sku} • {alert.location_name}</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-bold">{alert.current_stock} units</div>
                            <div className="text-sm text-muted-foreground">
                              Reorder at {alert.reorder_point}
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        No inventory alerts for this period
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="channels">
              <Card>
                <CardHeader>
                  <CardTitle>Channel Performance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {report.channel_insights.map((channel) => (
                      <div key={channel.channel} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center gap-4">
                          <Badge variant="outline">{channel.market_share_percent.toFixed(1)}%</Badge>
                          <div>
                            <div className="font-medium">{channel.channel}</div>
                            <div className="text-sm text-muted-foreground">{channel.orders} orders</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold">${channel.revenue.toLocaleString()}</div>
                          <div className="text-sm text-muted-foreground">
                            {channel.units} units
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
'use client';

import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { useSalesAnalytics } from '@/hooks/use-sales-analytics';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';

interface SalesTrendChartProps {
  days?: number;
  className?: string;
}

export function SalesTrendChart({ days = 30, className }: SalesTrendChartProps) {
  const { data, isLoading: loading, error } = useSalesAnalytics(days);

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Sales Trend
          </CardTitle>
          <CardDescription>Daily revenue and units sold over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            <div className="animate-pulse">Loading chart data...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Sales Trend
          </CardTitle>
          <CardDescription>Daily revenue and units sold over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p>Unable to load chart data</p>
              <p className="text-sm mt-1 text-muted-foreground">
                {error?.message || 'Data not available for the selected time period'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data?.daily_sales || data.daily_sales.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Sales Trend
          </CardTitle>
          <CardDescription>Daily revenue and units sold over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No sales data available for the selected period
          </div>
        </CardContent>
      </Card>
    );
  }

  // Aggregate daily sales by date
  const chartData = data.daily_sales.reduce((acc, sale) => {
    const date = sale.sales_date;
    const existing = acc.find(item => item.date === date);
    
    if (existing) {
      existing.revenue += sale.gross_revenue;
      existing.units += sale.units_sold;
      existing.orders += sale.orders_count;
    } else {
      acc.push({
        date,
        revenue: sale.gross_revenue,
        units: sale.units_sold,
        orders: sale.orders_count,
        formattedDate: new Date(date).toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric' 
        })
      });
    }
    
    return acc;
  }, [] as Array<{
    date: string;
    revenue: number;
    units: number;
    orders: number;
    formattedDate: string;
  }>);

  // Sort by date
  chartData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Sales Trend
        </CardTitle>
        <CardDescription>
          Daily revenue and units sold over the last {days} days
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis 
              dataKey="formattedDate" 
              className="text-xs fill-muted-foreground"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
            />
            <YAxis 
              yAxisId="revenue"
              orientation="left"
              className="text-xs fill-muted-foreground"
              tick={{ fontSize: 10 }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              width={60}
            />
            <YAxis 
              yAxisId="units"
              orientation="right"
              className="text-xs fill-muted-foreground"
              tick={{ fontSize: 10 }}
              tickFormatter={(value) => `${value}`}
              width={40}
            />
            <Tooltip 
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-background border rounded-lg shadow-lg p-3">
                      <p className="font-medium">{label}</p>
                      {payload.map((entry, index) => (
                        <p key={index} style={{ color: entry.color }}>
                          {entry.name}: {
                            entry.dataKey === 'revenue' 
                              ? `$${entry.value?.toLocaleString()}` 
                              : entry.value?.toLocaleString()
                          }
                        </p>
                      ))}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend />
            <Line 
              yAxisId="revenue"
              type="monotone" 
              dataKey="revenue" 
              stroke="#0088FE" 
              strokeWidth={2}
              name="Revenue ($)"
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line 
              yAxisId="units"
              type="monotone" 
              dataKey="units" 
              stroke="#00C49F" 
              strokeWidth={2}
              name="Units Sold"
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
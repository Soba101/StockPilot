'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';
import { useDashboard } from '@/hooks/use-dashboard';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Package, TrendingUp, DollarSign, Activity, ShoppingCart, RefreshCw, Calendar } from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { SalesTrendChart } from '@/components/charts/sales-trend-chart';
import { DashboardSkeleton } from '@/components/dashboard/dashboard-skeleton';
import { KPICard } from '@/components/dashboard/kpi-card';
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function DashboardPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [timePeriod, setTimePeriod] = useState(30);
  const { stats, loading: dashboardLoading, error, refetch } = useDashboard(timePeriod);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  // Use stats from enhanced dashboard hook with fallback
  const metrics = stats || {
    totalProducts: 0,
    lowStockCount: 0,
    outOfStockCount: 0,
    totalValue: 0,
    topCategories: [],
    recentActivity: [],
    trends: {
      revenue: { current: 0, previous: 0, direction: 'neutral' as const, percentage: 0 },
      units: { current: 0, previous: 0, direction: 'neutral' as const, percentage: 0 },
      orders: { current: 0, previous: 0, direction: 'neutral' as const, percentage: 0 },
    }
  };

  if (isLoading || dashboardLoading) {
    return <DashboardSkeleton />;
  }

  if (!isAuthenticated) {
    return null;
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center text-red-600">
          <p>Error loading dashboard data: {error}</p>
          <Button onClick={() => window.location.reload()} className="mt-4">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground text-sm sm:text-base">Welcome to your inventory management dashboard</p>
        </div>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="inline-flex rounded-md border overflow-hidden">
            {[7, 30, 90].map((days) => (
              <Button
                key={days}
                size="sm"
                variant={timePeriod === days ? 'default' : 'ghost'}
                className="rounded-none"
                onClick={() => setTimePeriod(days)}
              >
                <Calendar className="h-4 w-4 mr-2" />
                {days}d
              </Button>
            ))}
          </div>
          <Button 
            onClick={refetch} 
            disabled={dashboardLoading}
            variant="outline"
            size="sm"
            className="flex items-center gap-2 w-full sm:w-auto"
          >
            <RefreshCw className={`h-4 w-4 ${dashboardLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Revenue"
          value={`$${metrics.trends?.revenue.current.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}`}
          description={`Last ${timePeriod} days`}
          icon={DollarSign}
          trend={metrics.trends?.revenue ? {
            value: metrics.trends.revenue.percentage,
            label: `vs prev ${timePeriod}d`,
            direction: metrics.trends.revenue.direction
          } : undefined}
        />
        <KPICard
          title="Units Sold"
          value={metrics.trends?.units.current || 0}
          description={`Last ${timePeriod} days`}
          icon={Package}
          trend={metrics.trends?.units ? {
            value: metrics.trends.units.percentage,
            label: `vs prev ${timePeriod}d`,
            direction: metrics.trends.units.direction
          } : undefined}
        />
        <KPICard
          title="Low Stock Items"
          value={metrics.lowStockCount}
          description="Need reordering soon"
          icon={AlertTriangle}
        />
        <KPICard
          title="Out of Stock"
          value={metrics.outOfStockCount}
          description="Immediate attention needed"
          icon={AlertTriangle}
        />
      </div>

      {/* Sales Trend Chart */}
      <SalesTrendChart days={timePeriod} className="w-full" />

      <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
        {/* Category Distribution Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Product Categories</CardTitle>
            <CardDescription>Distribution of products by category</CardDescription>
          </CardHeader>
          <CardContent>
            {metrics.topCategories.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={metrics.topCategories}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {metrics.topCategories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                No category data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest inventory movements and updates</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {metrics.recentActivity.map((activity, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <Activity className="h-4 w-4 text-blue-500" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{activity.action}</p>
                    <p className="text-xs text-muted-foreground">{activity.product}</p>
                  </div>
                  <div className="text-xs text-muted-foreground">{activity.timestamp}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks to help you manage your inventory</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            <Button asChild>
              <Link href="/products/new">
                <Package className="mr-2 h-4 w-4" />
                Add Product
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/analytics/import">
                <TrendingUp className="mr-2 h-4 w-4" />
                Import Data
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/purchasing/new">
                <ShoppingCart className="mr-2 h-4 w-4" />
                Create Purchase Order
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/analytics/reports">
                <Activity className="mr-2 h-4 w-4" />
                View Reports
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stock Alerts Summary */}
      {(metrics.lowStockCount > 0 || metrics.outOfStockCount > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Stock Alerts Summary
            </CardTitle>
            <CardDescription>Items that need immediate attention</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="text-sm font-medium text-red-600">Out of Stock</p>
                  <p className="text-2xl font-bold text-red-600">{metrics.outOfStockCount}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-red-500" />
              </div>
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="text-sm font-medium text-yellow-600">Low Stock</p>
                  <p className="text-2xl font-bold text-yellow-600">{metrics.lowStockCount}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-yellow-500" />
              </div>
            </div>
            <div className="mt-4 text-center">
              <Button asChild variant="outline">
                <Link href="/products?filter=low_stock">View All Products</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      </div>
    </div>
  );
}
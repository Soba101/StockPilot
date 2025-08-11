'use client'

import { useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign,
  Package,
  BarChart3,
  PieChart,
  Calendar,
  Filter
} from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Area,
} from 'recharts'
import { useAnalytics } from '@/hooks/use-analytics'

export default function AnalyticsPage() {
  // UI state: date range & filters
  const [rangeDays, setRangeDays] = useState<7 | 30 | 90>(30)
  const [showFilters, setShowFilters] = useState(false)
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['Online', 'POS', 'Phone'])

  // Fetch real analytics data
  const { data: analytics, loading, error, refetch } = useAnalytics(rangeDays)

  const toggleChannel = (ch: string) => {
    setSelectedChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    )
  }

  // Apply channel filter to recent sales
  const filteredRecentSales = useMemo(() => {
    if (!analytics?.recentSales) return []
    return analytics.recentSales.filter((s) => selectedChannels.includes(s.channel))
  }, [analytics?.recentSales, selectedChannels])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading analytics...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-destructive">Error loading analytics: {error}</div>
      </div>
    )
  }

  if (!analytics) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">No analytics data available</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Sales Analytics</h1>
          <p className="text-muted-foreground">
            Analyze sales trends, margins, and performance
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <div className="inline-flex rounded-md border overflow-hidden">
            {[7, 30, 90].map((d) => (
              <Button
                key={d}
                size="sm"
                variant={rangeDays === d ? 'default' : 'ghost'}
                className="rounded-none"
                onClick={() => setRangeDays(d as 7 | 30 | 90)}
              >
                <Calendar className="h-4 w-4 mr-2" />
                Last {d} Days
              </Button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowFilters((v) => !v)}>
            <Filter className="h-4 w-4 mr-2" />
            {showFilters ? 'Hide Filters' : 'Filter'}
          </Button>
        </div>
      </div>

      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Filters</CardTitle>
            <CardDescription>Refine data displayed on this page</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted-foreground mr-2">Channels:</span>
              {['Online', 'POS', 'Phone'].map((ch) => (
                <Button
                  key={ch}
                  size="sm"
                  variant={selectedChannels.includes(ch) ? 'default' : 'outline'}
                  onClick={() => toggleChannel(ch)}
                >
                  {ch}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${analytics.salesMetrics.totalRevenue.toLocaleString()}</div>
            <p className="text-xs text-green-600 flex items-center">
              <TrendingUp className="h-3 w-3 mr-1" />
              +{analytics.salesMetrics.revenueGrowth}% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Units Sold</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.salesMetrics.totalUnits.toLocaleString()}</div>
            <p className="text-xs text-red-600 flex items-center">
              <TrendingDown className="h-3 w-3 mr-1" />
              {analytics.salesMetrics.unitsGrowth}% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Order Value</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${analytics.salesMetrics.avgOrderValue.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              Across {analytics.salesMetrics.totalOrders} orders
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.salesMetrics.totalOrders.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              This period
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Top Products */}
        <Card>
          <CardHeader>
            <CardTitle>Top Performing Products</CardTitle>
            <CardDescription>
              Products ranked by revenue in the last 30 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead className="text-right">Units</TableHead>
                  <TableHead className="text-right">Revenue</TableHead>
                  <TableHead className="text-right">Margin</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analytics.topProducts.map((product, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{product.name}</div>
                        <div className="text-sm text-muted-foreground">{product.sku}</div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">{product.units}</TableCell>
                    <TableCell className="text-right">${product.revenue.toLocaleString()}</TableCell>
                    <TableCell className="text-right">
                      <span className="text-green-600">{product.margin}%</span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Category Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Category Performance</CardTitle>
            <CardDescription>
              Revenue breakdown by product category
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analytics.categoryData.map((category, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">{category.category}</span>
                    <span className="text-sm text-muted-foreground">
                      ${category.revenue.toLocaleString()} ({category.percentage}%)
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 bg-muted rounded-full h-2">
                      <div 
                        className="bg-primary rounded-full h-2" 
                        style={{ width: `${category.percentage}%` }}
                      />
                    </div>
                    <span className={`text-xs flex items-center ${
                      category.growth > 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {category.growth > 0 ? 
                        <TrendingUp className="h-3 w-3 mr-1" /> : 
                        <TrendingDown className="h-3 w-3 mr-1" />
                      }
                      {Math.abs(category.growth)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Sales */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Sales Transactions</CardTitle>
          <CardDescription>
            Latest sales activity across all channels
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Product</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead className="text-right">Revenue</TableHead>
                <TableHead>Channel</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRecentSales.map((sale, index) => (
                <TableRow key={index}>
                  <TableCell>{sale.date}</TableCell>
                  <TableCell className="font-medium">{sale.product}</TableCell>
                  <TableCell className="text-right">{sale.quantity}</TableCell>
                  <TableCell className="text-right">${sale.revenue.toFixed(2)}</TableCell>
                  <TableCell>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      sale.channel === 'Online' ? 'bg-blue-100 text-blue-800' :
                      sale.channel === 'POS' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {sale.channel}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Revenue Trend Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Revenue Trend</CardTitle>
          <CardDescription>
            Daily revenue for the last {rangeDays} days
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.revenueTrend} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" className="text-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={(v) => `$${v.toLocaleString()}`} width={70} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v: number) => [`$${v.toLocaleString()}`, 'Revenue']} labelClassName="text-xs" />
                <Area type="monotone" dataKey="revenue" stroke="#0ea5e9" fill="#0ea5e933" strokeWidth={2} />
                <Line type="monotone" dataKey="revenue" stroke="#0ea5e9" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
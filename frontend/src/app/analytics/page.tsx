'use client'

import { useMemo, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
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
import { useSalesAnalytics } from '@/hooks/use-sales-analytics'
import { useStockoutRisk } from '@/hooks/use-stockout-risk'

export default function AnalyticsPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  
  // UI state: date range & filters
  const [rangeDays, setRangeDays] = useState<7 | 30 | 90>(30)
  const [showFilters, setShowFilters] = useState(false)
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['Online', 'POS', 'Phone', 'b2b_portal'])

  // Fetch real analytics data
  const { data: analytics, loading, error, refetch } = useAnalytics(rangeDays)
  const { data: salesAnalytics } = useSalesAnalytics(rangeDays)
  const { data: stockoutRisk } = useStockoutRisk(rangeDays)

  // Auth guard
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // Return loading or null while checking auth
  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  const toggleChannel = (ch: string) => {
    setSelectedChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    )
  }

  // Apply channel filter to recent sales
  const filteredRecentSales = useMemo(() => {
    if (!analytics?.recent_sales) return []
    return analytics.recent_sales.filter((s) => selectedChannels.includes(s.channel))
  }, [analytics?.recent_sales, selectedChannels])

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
              {['Online', 'POS', 'Phone', 'b2b_portal'].map((ch) => (
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
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${analytics.sales_metrics.total_revenue.toLocaleString()}</div>
            <p className="text-xs text-green-600 flex items-center">
              <TrendingUp className="h-3 w-3 mr-1" />
              +{analytics.sales_metrics.revenue_growth}% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Units Sold</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.sales_metrics.total_units.toLocaleString()}</div>
            <p className="text-xs text-red-600 flex items-center">
              <TrendingDown className="h-3 w-3 mr-1" />
              {analytics.sales_metrics.units_growth}% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Order Value</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${analytics.sales_metrics.avg_order_value.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              Across {analytics.sales_metrics.total_orders} orders
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.sales_metrics.total_orders.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              This period
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Margin %</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(salesAnalytics?.period_summary?.avg_margin_percent ?? 0).toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">Gross margin for period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Velocity (Median)</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(() => {
              if (!salesAnalytics?.daily_sales?.length) return '—'
              const vals = salesAnalytics.daily_sales.map(r => r.units_7day_avg).filter(v => v > 0).sort((a,b)=>a-b)
              if (!vals.length) return '—'
              const mid = Math.floor(vals.length / 2)
              const median = vals.length % 2 ? vals[mid] : (vals[mid-1]+vals[mid])/2
              return median.toFixed(1)
            })()}</div>
            <p className="text-xs text-muted-foreground">Median 7d avg units</p>
          </CardContent>
        </Card>
      </div>

      {/* Stockout Risk (Days to Stockout) */}
      <Card>
        <CardHeader>
          <CardTitle>Stockout Risk</CardTitle>
          <CardDescription>
            Prioritized by risk & estimated days to stockout (range {rangeDays}d velocity)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead className="text-right">On Hand</TableHead>
                  <TableHead className="text-right">7d Avg</TableHead>
                  <TableHead className="text-right">30d Avg</TableHead>
                  <TableHead className="text-right">Days to Stockout</TableHead>
                  <TableHead className="text-right">Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stockoutRisk?.slice(0, 10).map(r => (
                  <TableRow key={r.product_id}>
                    <TableCell>
                      <div className="font-medium">{r.product_name}</div>
                      <div className="text-xs text-muted-foreground">{r.sku}</div>
                    </TableCell>
                    <TableCell className="text-right">{r.on_hand}</TableCell>
                    <TableCell className="text-right">{r.velocity_7d?.toFixed(1) ?? '—'}</TableCell>
                    <TableCell className="text-right">{r.velocity_30d?.toFixed(1) ?? '—'}</TableCell>
                    <TableCell className="text-right">{r.days_to_stockout?.toFixed(1) ?? '—'}</TableCell>
                    <TableCell className="text-right">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                        r.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                        r.risk_level === 'medium' ? 'bg-amber-100 text-amber-700' :
                        r.risk_level === 'low' ? 'bg-yellow-50 text-yellow-700' :
                        'bg-green-50 text-green-700'
                      }`}>{r.risk_level}</span>
                    </TableCell>
                  </TableRow>
                ))}
                {(!stockoutRisk || stockoutRisk.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-sm text-muted-foreground">No risk data</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          {stockoutRisk?.length ? (
            <div className="mt-4 flex justify-end">
              <Button size="sm" variant="outline" onClick={() => {
                const csv = ['product,sku,on_hand,velocity_7d,velocity_30d,days_to_stockout,risk_level']
                stockoutRisk.forEach(r => {
                  csv.push([
                    JSON.stringify(r.product_name),
                    r.sku,
                    r.on_hand,
                    r.velocity_7d ?? '',
                    r.velocity_30d ?? '',
                    r.days_to_stockout ?? '',
                    r.risk_level
                  ].join(','))
                })
                const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `stockout-risk-${rangeDays}d.csv`
                a.click()
                URL.revokeObjectURL(url)
              }}>Export CSV</Button>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Channel Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Channel Performance</CardTitle>
          <CardDescription>Revenue & margin by sales channel</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Channel</TableHead>
                <TableHead className="text-right">Revenue</TableHead>
                <TableHead className="text-right">Units</TableHead>
                <TableHead className="text-right">Orders</TableHead>
                <TableHead className="text-right">Avg Order</TableHead>
                <TableHead className="text-right">Margin %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {salesAnalytics?.channel_performance?.map(ch => (
                <TableRow key={ch.channel}>
                  <TableCell>{ch.channel || 'Unknown'}</TableCell>
                  <TableCell className="text-right">${ch.total_revenue.toLocaleString()}</TableCell>
                  <TableCell className="text-right">{ch.total_units}</TableCell>
                  <TableCell className="text-right">{ch.orders_count}</TableCell>
                  <TableCell className="text-right">${ch.avg_order_value.toFixed(2)}</TableCell>
                  <TableCell className="text-right">{ch.margin_percent.toFixed(1)}%</TableCell>
                </TableRow>
              ))}
              {(!salesAnalytics?.channel_performance || salesAnalytics.channel_performance.length===0) && (
                <TableRow><TableCell colSpan={6} className="text-center text-sm text-muted-foreground">No channel data</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Data Export */}
      <Card>
        <CardHeader>
          <CardTitle>Export & Drill-down</CardTitle>
          <CardDescription>Download consolidated analytics datasets</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => {
              const datasets: Record<string, any[]> = {
                revenue_trend: analytics.revenue_trend || [],
                top_products: analytics.top_products || [],
                category_data: analytics.category_data || [],
                channel_performance: salesAnalytics?.channel_performance || [],
                stockout_risk: stockoutRisk || []
              }
              const blob = new Blob([JSON.stringify({ rangeDays, exported_at: new Date().toISOString(), datasets }, null, 2)], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `analytics-export-${rangeDays}d.json`
              a.click()
              URL.revokeObjectURL(url)
            }}>Export JSON</Button>
            <Button size="sm" variant="outline" onClick={() => {
              const csvLines: string[] = []
              csvLines.push('dataset,type,a,b,c,d,e,f,g')
              analytics.top_products.forEach(p=>csvLines.push(`top_product,${p.sku},${p.name},${p.units},${p.revenue},${p.margin}`))
              salesAnalytics?.channel_performance?.forEach(ch=>csvLines.push(`channel,${ch.channel},${ch.total_revenue},${ch.total_units},${ch.orders_count},${ch.avg_order_value},${ch.margin_percent}`))
              stockoutRisk?.forEach(r=>csvLines.push(`stockout,${r.sku},${r.product_name},${r.on_hand},${r.velocity_7d},${r.velocity_30d},${r.days_to_stockout},${r.risk_level}`))
              const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `analytics-export-${rangeDays}d.csv`
              a.click()
              URL.revokeObjectURL(url)
            }}>Export CSV (Summary)</Button>
            <Button size="sm" onClick={()=>refetch()}>Refresh Now</Button>
          </div>
        </CardContent>
      </Card>

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
                {analytics.top_products.map((product, index) => (
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
              {analytics.category_data.map((category, index) => (
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
              <LineChart data={analytics.revenue_trend} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
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
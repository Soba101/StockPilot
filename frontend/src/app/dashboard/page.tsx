'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Link from 'next/link'
import { 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  Package, 
  DollarSign,
  ShoppingCart,
  Clock,
  AlertCircle
} from 'lucide-react'

// Mock data - will be replaced with real API calls
const mockKPIs = {
  totalProducts: 156,
  totalValue: 45780,
  lowStock: 12,
  outOfStock: 3,
  totalSales: 28450,
  avgMargin: 35.2
}

const mockStockoutRisks = [
  { sku: 'WIDGET-001', name: 'Blue Widget', currentStock: 5, daysUntilStockout: 3, velocity: 1.7 },
  { sku: 'GADGET-001', name: 'Super Gadget', currentStock: 2, daysUntilStockout: 6, velocity: 0.3 },
  { sku: 'WIDGET-002', name: 'Red Widget', currentStock: 8, daysUntilStockout: 8, velocity: 1.0 },
]

const mockRecentActivity = [
  { type: 'sale', item: 'Blue Widget', quantity: 5, timestamp: '2 hours ago' },
  { type: 'restock', item: 'Super Gadget', quantity: 25, timestamp: '4 hours ago' },
  { type: 'adjustment', item: 'Red Widget', quantity: -2, timestamp: '6 hours ago' },
]

export default function DashboardPage() {
  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your inventory performance and key metrics
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Products</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockKPIs.totalProducts}</div>
            <p className="text-xs text-muted-foreground">
              Active SKUs in catalog
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Inventory Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${mockKPIs.totalValue.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Total inventory cost
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Low Stock Items</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{mockKPIs.lowStock}</div>
            <p className="text-xs text-muted-foreground">
              Below reorder point
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Out of Stock</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{mockKPIs.outOfStock}</div>
            <p className="text-xs text-muted-foreground">
              Zero inventory
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Sales</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${mockKPIs.totalSales.toLocaleString()}</div>
            <p className="text-xs text-green-600">
              +12% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Margin</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockKPIs.avgMargin}%</div>
            <p className="text-xs text-muted-foreground">
              Gross profit margin
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Stockout Risks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Stockout Risks
            </CardTitle>
            <CardDescription>
              Products at risk of stocking out in the next 14 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead>Days Left</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockStockoutRisks.map((item, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{item.name}</div>
                        <div className="text-sm text-muted-foreground">{item.sku}</div>
                      </div>
                    </TableCell>
                    <TableCell>{item.currentStock}</TableCell>
                    <TableCell>
                      <div className={`font-medium ${
                        item.daysUntilStockout <= 7 ? 'text-red-600' : 
                        item.daysUntilStockout <= 14 ? 'text-yellow-600' : 'text-green-600'
                      }`}>
                        {item.daysUntilStockout}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Button size="sm" variant="outline" asChild>
                        <Link href={`/purchasing/new?sku=${encodeURIComponent(item.sku)}`}>
                          Reorder
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>
              Latest inventory movements and transactions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockRecentActivity.map((activity, index) => (
                <div key={index} className="flex items-center space-x-4">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    activity.type === 'sale' ? 'bg-green-100 text-green-600' :
                    activity.type === 'restock' ? 'bg-blue-100 text-blue-600' :
                    'bg-yellow-100 text-yellow-600'
                  }`}>
                    {activity.type === 'sale' ? <TrendingDown className="w-4 h-4" /> :
                     activity.type === 'restock' ? <TrendingUp className="w-4 h-4" /> :
                     <AlertTriangle className="w-4 h-4" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between">
                      <span className="font-medium">
                        {activity.type === 'sale' ? 'Sale' :
                         activity.type === 'restock' ? 'Restock' : 'Adjustment'}
                      </span>
                      <span className="text-sm text-muted-foreground">{activity.timestamp}</span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {activity.item} ({activity.quantity > 0 ? '+' : ''}{activity.quantity})
                    </div>
                  </div>
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
          <CardDescription>
            Common tasks and shortcuts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button asChild>
              <Link href="/products/new">
                <Package className="mr-2 h-4 w-4" />
                Add Product
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/analytics/import">
                <TrendingUp className="mr-2 h-4 w-4" />
                Import Sales Data
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/purchasing/new">
                <ShoppingCart className="mr-2 h-4 w-4" />
                Create Purchase Order
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/analytics/reports">
                Generate Report
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
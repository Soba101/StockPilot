'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Package, Search, Plus, ArrowRightLeft, RefreshCw, TrendingDown } from 'lucide-react';
import { useInventory } from '@/hooks/use-inventory';

export default function InventoryPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const { summary, loading, error, refetch } = useInventory();
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading inventory...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-500">Error loading inventory: {error.message}</div>
      </div>
    );
  }

  const filteredProducts = summary?.locations.flatMap(location => 
    location.products.filter(product =>
      product.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.product_sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
      location.location_name.toLowerCase().includes(searchTerm.toLowerCase())
    ).map(product => ({ ...product, location_name: location.location_name }))
  ) || [];

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Inventory Management</h1>
        <p className="text-gray-600 mt-2">Track and manage stock levels across all locations</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Products</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_products || 0}</div>
            <p className="text-xs text-muted-foreground">
              Across {summary?.total_locations || 0} locations
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Low Stock Items</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{summary?.low_stock_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              Need reordering
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Out of Stock</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{summary?.out_of_stock_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              Immediate attention required
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Stock Value</CardTitle>
            <Package className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${(summary?.total_stock_value || 0).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              Current inventory value
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-4 mb-6">
        <Button asChild>
          <Link href="/inventory/adjust">
            <Plus className="w-4 h-4 mr-2" />
            Adjust Stock
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/inventory/transfer">
            <ArrowRightLeft className="w-4 h-4 mr-2" />
            Transfer Stock
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/inventory/movements">
            <RefreshCw className="w-4 h-4 mr-2" />
            Movement History
          </Link>
        </Button>
        <Button variant="outline" onClick={refetch}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Search and Filter */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Current Stock Levels</CardTitle>
          <CardDescription>
            Real-time inventory across all locations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2 mb-4">
            <Search className="w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search by product name, SKU, or location..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
            />
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>On Hand</TableHead>
                  <TableHead>Available</TableHead>
                  <TableHead>Reorder Point</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Movement</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProducts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-4">
                      No inventory data found.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredProducts.map((product, index) => (
                    <TableRow key={`${product.product_id}-${product.location_id}-${index}`}>
                      <TableCell className="font-medium">
                        {product.product_name}
                      </TableCell>
                      <TableCell>{product.product_sku}</TableCell>
                      <TableCell>{product.location_name}</TableCell>
                      <TableCell>{product.on_hand_quantity}</TableCell>
                      <TableCell>{product.available_quantity}</TableCell>
                      <TableCell>{product.reorder_point || 'Not set'}</TableCell>
                      <TableCell>
                        {product.is_out_of_stock ? (
                          <Badge variant="destructive">Out of Stock</Badge>
                        ) : product.is_low_stock ? (
                          <Badge variant="outline" className="border-yellow-600 text-yellow-600">
                            Low Stock
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="border-green-600 text-green-600">
                            In Stock
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {product.last_movement_date
                          ? new Date(product.last_movement_date).toLocaleDateString()
                          : 'Never'
                        }
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
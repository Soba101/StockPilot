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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowLeft, Search, RefreshCw, TrendingUp, TrendingDown, ArrowRightLeft, Settings } from 'lucide-react';
import { useInventoryMovements } from '@/hooks/use-inventory';

export default function MovementsPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  
  const [filters, setFilters] = useState({
    productId: '',
    locationId: '',
    movementType: '',
    startDate: '',
    endDate: '',
  });
  
  const [searchTerm, setSearchTerm] = useState('');
  
  const { data: movements, isLoading: movementsLoading, error, refetch } = useInventoryMovements({
    ...filters,
    skip: 0,
    limit: 100,
  });

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || movementsLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading movements...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-500">Error loading movements: {error.message}</div>
      </div>
    );
  }

  const filteredMovements = movements?.filter(movement =>
    movement.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    movement.product_sku?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    movement.location_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    movement.reference?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const getMovementTypeIcon = (type: string) => {
    switch (type) {
      case 'in':
        return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'out':
        return <TrendingDown className="w-4 h-4 text-red-600" />;
      case 'adjust':
        return <Settings className="w-4 h-4 text-blue-600" />;
      case 'transfer':
        return <ArrowRightLeft className="w-4 h-4 text-purple-600" />;
      default:
        return null;
    }
  };

  const getMovementTypeBadge = (type: string) => {
    const variants = {
      in: 'outline',
      out: 'outline', 
      adjust: 'outline',
      transfer: 'outline'
    } as const;
    
    const colors = {
      in: 'border-green-600 text-green-600',
      out: 'border-red-600 text-red-600',
      adjust: 'border-blue-600 text-blue-600',
      transfer: 'border-purple-600 text-purple-600'
    };

    return (
      <Badge variant={variants[type as keyof typeof variants]} className={colors[type as keyof typeof colors]}>
        {type.charAt(0).toUpperCase() + type.slice(1)}
      </Badge>
    );
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" asChild>
            <Link href="/inventory">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Inventory
            </Link>
          </Button>
        </div>
        <h1 className="text-3xl font-bold mt-4">Movement History</h1>
        <p className="text-gray-600 mt-2">Track all inventory transactions and movements</p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filter Movements</CardTitle>
          <CardDescription>
            Search and filter inventory movements
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4">
            <div className="flex items-center space-x-2">
              <Search className="w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            
            <Select value={filters.movementType} onValueChange={(value) => setFilters({...filters, movementType: value})}>
              <SelectTrigger>
                <SelectValue placeholder="Movement Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                <SelectItem value="in">Stock In</SelectItem>
                <SelectItem value="out">Stock Out</SelectItem>
                <SelectItem value="adjust">Adjustment</SelectItem>
                <SelectItem value="transfer">Transfer</SelectItem>
              </SelectContent>
            </Select>
            
            <Input
              type="date"
              placeholder="Start Date"
              value={filters.startDate}
              onChange={(e) => setFilters({...filters, startDate: e.target.value})}
            />
            
            <Input
              type="date"
              placeholder="End Date"
              value={filters.endDate}
              onChange={(e) => setFilters({...filters, endDate: e.target.value})}
            />
            
            <Button onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Movements Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Movements</CardTitle>
          <CardDescription>
            Latest {filteredMovements.length} movements
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Product</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Reference</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredMovements.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-4">
                      No movements found.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMovements.map((movement) => (
                    <TableRow key={movement.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getMovementTypeIcon(movement.movement_type)}
                          {getMovementTypeBadge(movement.movement_type)}
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">
                        {movement.product_name || 'Unknown Product'}
                      </TableCell>
                      <TableCell>{movement.product_sku || 'N/A'}</TableCell>
                      <TableCell>{movement.location_name || 'Unknown Location'}</TableCell>
                      <TableCell>
                        <span className={`font-semibold ${
                          movement.movement_type === 'in' || movement.movement_type === 'adjust' 
                            ? 'text-green-600' 
                            : 'text-red-600'
                        }`}>
                          {movement.movement_type === 'out' || movement.movement_type === 'transfer' ? '-' : '+'}
                          {movement.quantity}
                        </span>
                      </TableCell>
                      <TableCell>{movement.reference || '-'}</TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {movement.notes || '-'}
                      </TableCell>
                      <TableCell>
                        {new Date(movement.timestamp).toLocaleString()}
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
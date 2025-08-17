'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ArrowLeft, FileText, Package, Truck } from 'lucide-react'
import { usePurchaseOrder } from '@/hooks/use-purchasing'

export default function PurchaseOrderDetailPage() {
  const params = useParams()
  const id = params.id as string

  const { data: purchaseOrder, isLoading, error } = usePurchaseOrder(id)

  const formatStatus = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-8">Loading purchase order...</div>
      </div>
    )
  }

  if (error || !purchaseOrder) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent className="text-center py-8">
            <div className="text-red-600 mb-4">
              {error ? `Error: ${error}` : 'Purchase order not found'}
            </div>
            <Button asChild>
              <Link href="/purchasing">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Purchase Orders
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{purchaseOrder.po_number}</h1>
          <p className="text-muted-foreground">Purchase Order Details</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/purchasing">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Purchase Orders
            </Link>
          </Button>
        </div>
      </div>

      {/* Purchase Order Summary */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Order Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">PO Number</label>
                <p className="font-medium">{purchaseOrder.po_number}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Status</label>
                <p>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    purchaseOrder.status === 'draft' ? 'bg-gray-100 text-gray-800' :
                    purchaseOrder.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                    purchaseOrder.status === 'ordered' ? 'bg-blue-100 text-blue-800' :
                    purchaseOrder.status === 'received' ? 'bg-green-100 text-green-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {formatStatus(purchaseOrder.status)}
                  </span>
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Order Date</label>
                <p>{formatDate(purchaseOrder.order_date)}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Expected Date</label>
                <p>{formatDate(purchaseOrder.expected_date)}</p>
              </div>
              {purchaseOrder.received_date && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Received Date</label>
                  <p>{formatDate(purchaseOrder.received_date)}</p>
                </div>
              )}
              <div>
                <label className="text-sm font-medium text-muted-foreground">Total Amount</label>
                <p className="text-lg font-bold">{formatCurrency(purchaseOrder.total_amount)}</p>
              </div>
            </div>
            {purchaseOrder.notes && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">Notes</label>
                <p className="text-sm">{purchaseOrder.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5" />
              Supplier Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Supplier</label>
              <p className="font-medium">{purchaseOrder.supplier_name}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Order Items */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Order Items
          </CardTitle>
          <CardDescription>
            Items included in this purchase order
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead>SKU</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Unit Cost</TableHead>
                <TableHead>Total Cost</TableHead>
                <TableHead>Received</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {purchaseOrder.items && purchaseOrder.items.length > 0 ? (
                purchaseOrder.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">
                      {item.product_name || 'Unknown Product'}
                    </TableCell>
                    <TableCell>{item.product_sku || 'N/A'}</TableCell>
                    <TableCell>{item.quantity}</TableCell>
                    <TableCell>{formatCurrency(item.unit_cost)}</TableCell>
                    <TableCell>{formatCurrency(item.total_cost)}</TableCell>
                    <TableCell>
                      {item.received_quantity || 0} / {item.quantity}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No items found for this purchase order.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ArrowLeft, Plus, ShoppingCart } from 'lucide-react'

const mockPOs = [
  { id: 'PO-1001', sku: 'WIDGET-001', product: 'Blue Widget', qty: 50, supplier: 'Acme Supply', status: 'Pending' },
  { id: 'PO-1002', sku: 'GADGET-001', product: 'Super Gadget', qty: 25, supplier: 'Gizmo Corp', status: 'Ordered' },
]

export default function PurchasingPage() {
  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Purchasing</h1>
          <p className="text-muted-foreground">Create POs, manage suppliers, and restock inventory</p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href="/purchasing/new">
              <Plus className="h-4 w-4 mr-2" />
              Create Purchase Order
            </Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" />
            Recent Purchase Orders
          </CardTitle>
          <CardDescription>
            Track recent and pending purchase orders
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>PO #</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockPOs.map((po) => (
                <TableRow key={po.id}>
                  <TableCell className="font-medium">{po.id}</TableCell>
                  <TableCell>
                    <div>
                      <div className="font-medium">{po.product}</div>
                      <div className="text-sm text-muted-foreground">{po.sku}</div>
                    </div>
                  </TableCell>
                  <TableCell>{po.qty}</TableCell>
                  <TableCell>{po.supplier}</TableCell>
                  <TableCell>{po.status}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/purchasing/new?sku=${encodeURIComponent(po.sku)}`}>Reorder</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="mt-2">
        <Button variant="ghost" asChild>
          <Link href="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Link>
        </Button>
      </div>
    </div>
  )
}



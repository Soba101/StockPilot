'use client'

import Link from 'next/link'
import { useSearchParams, useRouter } from 'next/navigation'
import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Save } from 'lucide-react'

export default function NewPurchaseOrderPage() {
  const params = useSearchParams()
  const router = useRouter()
  const prefillSku = params.get('sku') || ''
  const [sku, setSku] = useState(prefillSku)
  const [quantity, setQuantity] = useState('10')
  const [supplier, setSupplier] = useState('Default Supplier')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  const createPO = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    // Placeholder action; wire to backend when PO API exists
    setTimeout(() => {
      setSaving(false)
      router.push('/purchasing')
    }, 600)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 flex items-center gap-4">
        <Button variant="ghost" asChild>
          <Link href="/purchasing">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Purchasing
          </Link>
        </Button>
      </div>
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Create Purchase Order</CardTitle>
          <CardDescription>Draft a quick PO for a product</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createPO} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="sku">Product SKU</Label>
                <Input id="sku" value={sku} onChange={(e) => setSku(e.target.value)} placeholder="WIDGET-001" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="qty">Quantity</Label>
                <Input id="qty" type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="supplier">Supplier</Label>
              <Input id="supplier" value={supplier} onChange={(e) => setSupplier(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional notes" />
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" asChild>
                <Link href="/purchasing">Cancel</Link>
              </Button>
              <Button type="submit" disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                {saving ? 'Creating...' : 'Create PO'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}



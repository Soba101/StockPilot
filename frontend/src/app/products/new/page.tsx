'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Save } from 'lucide-react'
import { productsApi } from '@/lib/api'
import { useOrganizations } from '@/hooks/use-organizations'

interface ProductForm {
  sku: string
  name: string
  description: string
  category: string
  cost: string
  price: string
  uom: string
  reorder_point: string
}

export default function NewProductPage() {
  const router = useRouter()
  const { currentOrg } = useOrganizations()
  const [form, setForm] = useState<ProductForm>({
    sku: '',
    name: '',
    description: '',
    category: '',
    cost: '',
    price: '',
    uom: 'each',
    reorder_point: '10'
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (!currentOrg) {
        throw new Error('No organization found')
      }

      const productData = {
        org_id: currentOrg.id,
        sku: form.sku,
        name: form.name,
        description: form.description || null,
        category: form.category || null,
        cost: form.cost ? parseFloat(form.cost) : null,
        price: form.price ? parseFloat(form.price) : null,
        uom: form.uom,
        reorder_point: parseInt(form.reorder_point)
      }

      await productsApi.create(productData)
      router.push('/products')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof ProductForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Button variant="ghost" asChild>
              <Link href="/products">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Products
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold">Add New Product</h1>
          <p className="text-muted-foreground">
            Create a new product in your catalog
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Product Information</CardTitle>
            <CardDescription>
              Enter the basic information for your new product
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="sku">SKU *</Label>
                  <Input
                    id="sku"
                    value={form.sku}
                    onChange={(e) => handleChange('sku', e.target.value)}
                    placeholder="e.g., WIDGET-001"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Product Name *</Label>
                  <Input
                    id="name"
                    value={form.name}
                    onChange={(e) => handleChange('name', e.target.value)}
                    placeholder="e.g., Blue Widget"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={form.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Product description..."
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Input
                    id="category"
                    value={form.category}
                    onChange={(e) => handleChange('category', e.target.value)}
                    placeholder="e.g., Widgets"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="uom">Unit of Measure</Label>
                  <Input
                    id="uom"
                    value={form.uom}
                    onChange={(e) => handleChange('uom', e.target.value)}
                    placeholder="e.g., each, box, kg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="cost">Cost ($)</Label>
                  <Input
                    id="cost"
                    type="number"
                    step="0.01"
                    value={form.cost}
                    onChange={(e) => handleChange('cost', e.target.value)}
                    placeholder="0.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="price">Selling Price ($)</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    value={form.price}
                    onChange={(e) => handleChange('price', e.target.value)}
                    placeholder="0.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reorder_point">Reorder Point</Label>
                  <Input
                    id="reorder_point"
                    type="number"
                    value={form.reorder_point}
                    onChange={(e) => handleChange('reorder_point', e.target.value)}
                    placeholder="10"
                  />
                </div>
              </div>

              {error && (
                <div className="text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="flex justify-end space-x-4">
                <Button type="button" variant="outline" asChild>
                  <Link href="/products">Cancel</Link>
                </Button>
                <Button type="submit" disabled={loading}>
                  <Save className="h-4 w-4 mr-2" />
                  {loading ? 'Creating...' : 'Create Product'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
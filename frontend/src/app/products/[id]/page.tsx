'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Save } from 'lucide-react'
import { useProduct } from '@/hooks/use-products'
import { productsApi } from '@/lib/api'

export default function EditProductPage() {
  const params = useParams<{ id: string }>()
  const productId = params?.id
  const router = useRouter()
  const { product, loading, error } = useProduct(productId)

  const [form, setForm] = useState({
    sku: '',
    name: '',
    description: '',
    category: '',
    cost: '',
    price: '',
    uom: 'each',
    reorder_point: '0',
  })
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    if (product) {
      setForm({
        sku: product.sku || '',
        name: product.name || '',
        description: product.description || '',
        category: product.category || '',
        cost: product.cost !== undefined && product.cost !== null ? String(product.cost) : '',
        price: product.price !== undefined && product.price !== null ? String(product.price) : '',
        uom: product.uom || 'each',
        reorder_point: String(product.reorder_point ?? 0),
      })
    }
  }, [product])

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!productId) return
    setSaving(true)
    setSaveError(null)
    try {
      await productsApi.update(productId, {
        sku: form.sku,
        name: form.name,
        description: form.description || null,
        category: form.category || null,
        cost: form.cost ? parseFloat(form.cost) : null,
        price: form.price ? parseFloat(form.price) : null,
        uom: form.uom,
        reorder_point: Number.parseInt(form.reorder_point || '0', 10),
      })
      router.push('/products')
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading product...</div>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center text-destructive">{error || 'Product not found'}</div>
        <div className="mt-4 flex justify-center">
          <Button variant="ghost" asChild>
            <Link href="/products">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Products
            </Link>
          </Button>
        </div>
      </div>
    )
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
          <h1 className="text-3xl font-bold">Edit Product</h1>
          <p className="text-muted-foreground">Update product details</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Product Information</CardTitle>
            <CardDescription>Update the details of this product</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="sku">SKU *</Label>
                  <Input id="sku" value={form.sku} onChange={(e) => handleChange('sku', e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Product Name *</Label>
                  <Input id="name" value={form.name} onChange={(e) => handleChange('name', e.target.value)} required />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" value={form.description} onChange={(e) => handleChange('description', e.target.value)} rows={3} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Input id="category" value={form.category} onChange={(e) => handleChange('category', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="uom">Unit of Measure</Label>
                  <Input id="uom" value={form.uom} onChange={(e) => handleChange('uom', e.target.value)} />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="cost">Cost ($)</Label>
                  <Input id="cost" type="number" step="0.01" value={form.cost} onChange={(e) => handleChange('cost', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="price">Selling Price ($)</Label>
                  <Input id="price" type="number" step="0.01" value={form.price} onChange={(e) => handleChange('price', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reorder_point">Reorder Point</Label>
                  <Input id="reorder_point" type="number" value={form.reorder_point} onChange={(e) => handleChange('reorder_point', e.target.value)} />
                </div>
              </div>

              {saveError && <div className="text-sm text-destructive">{saveError}</div>}

              <div className="flex justify-end space-x-4">
                <Button type="button" variant="outline" asChild>
                  <Link href="/products">Cancel</Link>
                </Button>
                <Button type="submit" disabled={saving}>
                  <Save className="h-4 w-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}



'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ArrowLeft, Upload, Download, CheckCircle } from 'lucide-react'
import { productsApi } from '@/lib/api'
import { useAuth } from '@/contexts/auth-context'

interface ImportPreview {
  sku: string
  name: string
  category?: string
  cost?: number
  price?: number
  reorder_point?: number
}

export default function ImportProductsPage() {
  const router = useRouter()
  const { user, isAuthenticated } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview[]>([])
  const [loading, setLoading] = useState(false)
  const [imported, setImported] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return

    setFile(selectedFile)
    setError(null)

    // Parse CSV file for preview
    try {
      const text = await selectedFile.text()
      const lines = text.split('\n')
      const headers = lines[0].split(',').map(h => h.trim())
      
      const data: ImportPreview[] = []
      for (let i = 1; i < Math.min(lines.length, 6); i++) { // Preview first 5 rows
        const values = lines[i].split(',').map(v => v.trim())
        if (values.length >= 2 && values[0] && values[1]) {
          data.push({
            sku: values[0],
            name: values[1],
            category: values[2] || undefined,
            cost: values[3] ? parseFloat(values[3]) : undefined,
            price: values[4] ? parseFloat(values[4]) : undefined,
            reorder_point: values[5] ? parseInt(values[5]) : 10
          })
        }
      }
      setPreview(data)
    } catch (err) {
      setError('Error reading file. Please make sure it\'s a valid CSV file.')
    }
  }

  const handleImport = async () => {
    if (!file) return

    setLoading(true)
    setError(null)

    try {
      if (!isAuthenticated || !user) {
        throw new Error('User not authenticated')
      }

      const text = await file.text()
      const lines = text.split('\n')
      
      const toUpsert = [] as any[]
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim())
        if (values.length >= 2 && values[0] && values[1]) {
          toUpsert.push({
            sku: values[0],
            name: values[1],
            category: values[2] || null,
            cost: values[3] ? parseFloat(values[3]) : null,
            price: values[4] ? parseFloat(values[4]) : null,
            uom: values[6] || 'each',
            reorder_point: values[5] ? parseInt(values[5]) : 10
          })
        }
      }

      if (toUpsert.length === 0) throw new Error('No valid rows found in CSV')

      await productsApi.bulkUpsert(toUpsert)
      setImported(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  const downloadTemplate = () => {
    const csvContent = 'SKU,Name,Category,Cost,Price,Reorder Point,Unit of Measure\nWIDGET-001,Blue Widget,Widgets,5.00,15.00,10,each\nGADGET-001,Super Gadget,Gadgets,25.00,75.00,5,each'
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'product-import-template.csv'
    a.click()
    window.URL.revokeObjectURL(url)
  }

  if (imported) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto text-center">
          <div className="mb-8">
            <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
            <h1 className="text-3xl font-bold">Import Successful!</h1>
            <p className="text-muted-foreground">
              Your products have been imported successfully
            </p>
          </div>
          <div className="space-x-4">
            <Button asChild>
              <Link href="/products">View Products</Link>
            </Button>
            <Button variant="outline" onClick={() => {
              setImported(false)
              setFile(null)
              setPreview([])
            }}>
              Import More
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Button variant="ghost" asChild>
              <Link href="/products">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Products
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold">Import Products</h1>
          <p className="text-muted-foreground">
            Upload a CSV file to import multiple products at once
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card>
            <CardHeader>
              <CardTitle>Upload CSV File</CardTitle>
              <CardDescription>
                Select a CSV file containing your product data
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="file">Choose CSV File</Label>
                <Input
                  id="file"
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                />
              </div>
              
              <Button
                variant="outline"
                onClick={downloadTemplate}
                className="w-full"
              >
                <Download className="h-4 w-4 mr-2" />
                Download CSV Template
              </Button>

              {error && (
                <div className="text-sm text-destructive">
                  {error}
                </div>
              )}

              {file && preview.length > 0 && (
                <Button
                  onClick={handleImport}
                  disabled={loading}
                  className="w-full"
                >
                  <Upload className="h-4 w-4 mr-2" />
                  {loading ? 'Importing...' : `Import ${preview.length} Products`}
                </Button>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>CSV Format Requirements</CardTitle>
              <CardDescription>
                Your CSV file should have these columns
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div><strong>SKU</strong> - Unique product identifier (required)</div>
                <div><strong>Name</strong> - Product name (required)</div>
                <div><strong>Category</strong> - Product category (optional)</div>
                <div><strong>Cost</strong> - Product cost in dollars (optional)</div>
                <div><strong>Price</strong> - Selling price in dollars (optional)</div>
                <div><strong>Reorder Point</strong> - Stock level to reorder (optional, defaults to 10)</div>
                <div><strong>Unit of Measure</strong> - e.g., each, box, kg (optional, defaults to "each")</div>
              </div>
            </CardContent>
          </Card>
        </div>

        {preview.length > 0 && (
          <Card className="mt-8">
            <CardHeader>
              <CardTitle>Preview</CardTitle>
              <CardDescription>
                First 5 rows from your CSV file
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Cost</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>Reorder Point</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{item.sku}</TableCell>
                      <TableCell>{item.name}</TableCell>
                      <TableCell>{item.category || '-'}</TableCell>
                      <TableCell>{item.cost ? `$${item.cost}` : '-'}</TableCell>
                      <TableCell>{item.price ? `$${item.price}` : '-'}</TableCell>
                      <TableCell>{item.reorder_point || 10}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
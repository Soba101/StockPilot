'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Upload } from 'lucide-react'

export default function ImportSalesPage() {
  const [file, setFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [message, setMessage] = useState('')

  const handleImport = async () => {
    if (!file) return
    setImporting(true)
    // Placeholder for future API
    setTimeout(() => {
      setMessage('Sales data imported successfully (demo).')
      setImporting(false)
    }, 700)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <Button variant="ghost" asChild>
          <Link href="/dashboard">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
        </Button>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Import Sales Data</CardTitle>
          <CardDescription>Upload a CSV with your sales transactions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="file">CSV File</Label>
            <Input id="file" type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
          <div className="flex gap-2">
            <Button onClick={handleImport} disabled={!file || importing}>
              <Upload className="h-4 w-4 mr-2" />
              {importing ? 'Importing...' : 'Import'}
            </Button>
            <Button variant="outline" asChild>
              <Link href="/analytics">Cancel</Link>
            </Button>
          </div>
          {message && <div className="text-sm text-green-600">{message}</div>}
        </CardContent>
      </Card>
    </div>
  )
}



'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft, FileDown } from 'lucide-react'

export default function ReportsPage() {
  const downloadReport = () => {
    const blob = new Blob([`Report generated at ${new Date().toISOString()}`], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'report.txt'
    a.click()
    URL.revokeObjectURL(url)
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
      <Card>
        <CardHeader>
          <CardTitle>Reports</CardTitle>
          <CardDescription>Generate and download reports</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={downloadReport}>
            <FileDown className="h-4 w-4 mr-2" />
            Download Sample Report
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}



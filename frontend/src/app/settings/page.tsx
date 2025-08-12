'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Settings, ArrowLeft } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useState } from 'react'

export default function SettingsPage() {
  const [orgName, setOrgName] = useState('Demo Company')
  const [allowedOrigins, setAllowedOrigins] = useState('http://localhost:3000')
  const [saving, setSaving] = useState(false)

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setTimeout(() => setSaving(false), 600) // stub
  }
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Configure your workspace</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Workspace
          </CardTitle>
          <CardDescription>Basic configuration (demo)</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={save} className="space-y-6 max-w-xl">
            <div className="space-y-2">
              <Label htmlFor="org">Organization Name</Label>
              <Input id="org" value={orgName} onChange={(e) => setOrgName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="origins">Allowed Origins (comma-separated)</Label>
              <Input id="origins" value={allowedOrigins} onChange={(e) => setAllowedOrigins(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save'}</Button>
              <Button variant="outline" asChild>
                <Link href="/">Back to Home</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="mt-8">
        <Button variant="ghost" asChild>
          <Link href="/dashboard">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Link>
        </Button>
      </div>
    </div>
  )
}



"use client"

import * as React from "react"
import { z } from "zod"
import { Plus, Settings, Trash2, RefreshCw, ExternalLink, CheckCircle, XCircle, AlertCircle, Globe, Webhook, Key } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useToast } from "@/components/ui/toast"

interface Integration {
  id: string
  name: string
  type: string
  description: string
  status: 'connected' | 'disconnected' | 'error' | 'pending'
  config: Record<string, any>
  lastSync?: string
  createdAt: string
  updatedAt: string
}

interface IntegrationTemplate {
  type: string
  name: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  fields: IntegrationField[]
  testEndpoint?: string
}

interface IntegrationField {
  key: string
  label: string
  type: 'text' | 'password' | 'url' | 'select' | 'textarea'
  required?: boolean
  placeholder?: string
  options?: { label: string; value: string }[]
  description?: string
}

interface IntegrationSettingsProps {
  className?: string
}

// Mock data for integrations
const MOCK_INTEGRATIONS: Integration[] = [
  {
    id: "1",
    name: "Shopify Store",
    type: "shopify",
    description: "Sync products and orders with Shopify",
    status: "connected",
    config: { store_url: "demo-store.myshopify.com", sync_products: true },
    lastSync: "2024-01-15T10:30:00Z",
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-15T10:30:00Z",
  },
  {
    id: "2", 
    name: "QuickBooks Online",
    type: "quickbooks",
    description: "Sync financial data with QuickBooks",
    status: "error",
    config: { company_id: "123456789", sync_enabled: false },
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-10T15:45:00Z",
  },
]

const INTEGRATION_TEMPLATES: IntegrationTemplate[] = [
  {
    type: "shopify",
    name: "Shopify",
    description: "Connect your Shopify store to sync products and orders",
    icon: Globe,
    fields: [
      { key: "store_url", label: "Store URL", type: "text", required: true, placeholder: "your-store.myshopify.com" },
      { key: "access_token", label: "Access Token", type: "password", required: true },
      { key: "sync_products", label: "Sync Products", type: "select", options: [{ label: "Yes", value: "true" }, { label: "No", value: "false" }] },
      { key: "webhook_secret", label: "Webhook Secret", type: "password", description: "Used to verify webhook authenticity" },
    ],
    testEndpoint: "/integrations/shopify/test",
  },
  {
    type: "quickbooks",
    name: "QuickBooks Online",
    description: "Sync financial data and accounting information",
    icon: Key,
    fields: [
      { key: "company_id", label: "Company ID", type: "text", required: true },
      { key: "client_id", label: "Client ID", type: "text", required: true },
      { key: "client_secret", label: "Client Secret", type: "password", required: true },
      { key: "redirect_uri", label: "Redirect URI", type: "url", required: true },
      { key: "sync_enabled", label: "Enable Sync", type: "select", options: [{ label: "Yes", value: "true" }, { label: "No", value: "false" }] },
    ],
    testEndpoint: "/integrations/quickbooks/test",
  },
  {
    type: "webhook",
    name: "Custom Webhook",
    description: "Configure custom webhook endpoints for external notifications",
    icon: Webhook,
    fields: [
      { key: "name", label: "Webhook Name", type: "text", required: true },
      { key: "url", label: "Endpoint URL", type: "url", required: true },
      { key: "method", label: "HTTP Method", type: "select", required: true, options: [
        { label: "POST", value: "POST" },
        { label: "PUT", value: "PUT" },
        { label: "PATCH", value: "PATCH" },
      ]},
      { key: "headers", label: "Custom Headers", type: "textarea", placeholder: "Authorization: Bearer token\nContent-Type: application/json" },
      { key: "events", label: "Trigger Events", type: "select", options: [
        { label: "Product Updates", value: "product_update" },
        { label: "Stock Changes", value: "stock_change" },
        { label: "Low Stock Alerts", value: "low_stock" },
      ]},
    ],
  },
]

export function IntegrationSettings({ className }: IntegrationSettingsProps) {
  const [integrations, setIntegrations] = React.useState<Integration[]>(MOCK_INTEGRATIONS)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = React.useState(false)
  const [selectedTemplate, setSelectedTemplate] = React.useState<IntegrationTemplate | null>(null)
  const [testingIntegration, setTestingIntegration] = React.useState<string | null>(null)
  const { toast } = useToast()

  const getStatusBadge = (status: Integration['status']) => {
    const styles = {
      connected: "bg-green-100 text-green-800",
      disconnected: "bg-gray-100 text-gray-800",
      error: "bg-red-100 text-red-800",
      pending: "bg-yellow-100 text-yellow-800",
    }
    const icons = {
      connected: <CheckCircle className="h-3 w-3" />,
      disconnected: <XCircle className="h-3 w-3" />,
      error: <AlertCircle className="h-3 w-3" />,
      pending: <RefreshCw className="h-3 w-3" />,
    }
    
    return (
      <Badge className={`${styles[status]} gap-1`} variant="secondary">
        {icons[status]}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    )
  }

  const handleTestConnection = async (integrationId: string) => {
    setTestingIntegration(integrationId)
    try {
      // Simulate API test call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      setIntegrations(prev => prev.map(integration => 
        integration.id === integrationId 
          ? { ...integration, status: 'connected' as const, lastSync: new Date().toISOString() }
          : integration
      ))
      
      toast({
        title: "Connection Test Successful",
        description: "Integration is working correctly",
      })
    } catch (error) {
      setIntegrations(prev => prev.map(integration => 
        integration.id === integrationId 
          ? { ...integration, status: 'error' as const }
          : integration
      ))
      
      toast({
        title: "Connection Test Failed",
        description: "Please check your configuration",
        variant: "destructive",
      })
    } finally {
      setTestingIntegration(null)
    }
  }

  const handleDeleteIntegration = (integrationId: string) => {
    setIntegrations(prev => prev.filter(integration => integration.id !== integrationId))
    toast({
      title: "Integration Removed",
      description: "Integration has been successfully removed",
    })
  }

  const handleCreateIntegration = (template: IntegrationTemplate) => {
    setSelectedTemplate(template)
    setIsCreateDialogOpen(true)
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <h3 className="text-lg font-medium">Integration Settings</h3>
        <p className="text-muted-foreground">
          Connect third-party services and configure webhooks
        </p>
      </div>

      <Tabs defaultValue="active" className="space-y-4">
        <TabsList>
          <TabsTrigger value="active">Active Integrations</TabsTrigger>
          <TabsTrigger value="available">Available Integrations</TabsTrigger>
        </TabsList>

        {/* Active Integrations */}
        <TabsContent value="active" className="space-y-4">
          {integrations.length > 0 ? (
            <div className="grid gap-4">
              {integrations.map((integration) => (
                <Card key={integration.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          <Settings className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{integration.name}</CardTitle>
                          <CardDescription>{integration.description}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusBadge(integration.status)}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <Settings className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuItem 
                              onClick={() => handleTestConnection(integration.id)}
                              disabled={testingIntegration === integration.id}
                            >
                              <RefreshCw className={`h-4 w-4 mr-2 ${testingIntegration === integration.id ? 'animate-spin' : ''}`} />
                              Test Connection
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Settings className="h-4 w-4 mr-2" />
                              Configure
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleDeleteIntegration(integration.id)}
                              className="text-red-600"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Remove
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Type:</span>
                        <div className="font-medium capitalize">{integration.type}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Last Sync:</span>
                        <div className="font-medium">
                          {integration.lastSync 
                            ? new Date(integration.lastSync).toLocaleString()
                            : "Never"
                          }
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Created:</span>
                        <div className="font-medium">
                          {new Date(integration.createdAt).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-8">
                  <Settings className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Integrations Configured</h3>
                  <p className="text-muted-foreground mb-4">
                    Connect your first third-party service to get started
                  </p>
                  <Button onClick={() => setIsCreateDialogOpen(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Integration
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Available Integrations */}
        <TabsContent value="available" className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h4 className="text-lg font-medium">Available Integrations</h4>
              <p className="text-muted-foreground">Choose from our supported third-party services</p>
            </div>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Integration
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {INTEGRATION_TEMPLATES.map((template) => {
              const Icon = template.icon
              const isConnected = integrations.some(i => i.type === template.type)
              
              return (
                <Card key={template.type} className="relative">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{template.name}</CardTitle>
                        <CardDescription className="text-sm">{template.description}</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex justify-between items-center">
                      {isConnected ? (
                        <Badge className="bg-green-100 text-green-800">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Connected
                        </Badge>
                      ) : (
                        <Badge variant="outline">Available</Badge>
                      )}
                      <Button
                        size="sm"
                        variant={isConnected ? "outline" : "default"}
                        onClick={() => handleCreateIntegration(template)}
                      >
                        {isConnected ? "Configure" : "Connect"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Integration Dialog */}
      <CreateIntegrationDialog
        isOpen={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        template={selectedTemplate}
        onSuccess={(newIntegration) => {
          setIntegrations(prev => [...prev, newIntegration])
          setIsCreateDialogOpen(false)
          setSelectedTemplate(null)
        }}
      />
    </div>
  )
}

interface CreateIntegrationDialogProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  template: IntegrationTemplate | null
  onSuccess: (integration: Integration) => void
}

function CreateIntegrationDialog({ isOpen, onOpenChange, template, onSuccess }: CreateIntegrationDialogProps) {
  const [formData, setFormData] = React.useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = React.useState(false)
  const [showPasswords, setShowPasswords] = React.useState(false)

  React.useEffect(() => {
    if (template) {
      const initialData: Record<string, string> = {}
      template.fields.forEach(field => {
        initialData[field.key] = ""
      })
      setFormData(initialData)
    }
  }, [template])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!template) return

    setIsLoading(true)
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      const newIntegration: Integration = {
        id: Date.now().toString(),
        name: formData.name || template.name,
        type: template.type,
        description: template.description,
        status: 'connected',
        config: formData,
        lastSync: new Date().toISOString(),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }

      onSuccess(newIntegration)
      
      toast({
        title: "Integration Added",
        description: `${template.name} has been successfully configured`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create integration",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  if (!template) return null

  const Icon = template.icon

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Connect {template.name}</DialogTitle>
              <DialogDescription>{template.description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {template.fields.map((field) => (
            <div key={field.key}>
              <Label htmlFor={field.key}>
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </Label>
              
              {field.type === 'select' && field.options ? (
                <Select
                  value={formData[field.key] || ""}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, [field.key]: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={`Select ${field.label.toLowerCase()}`} />
                  </SelectTrigger>
                  <SelectContent>
                    {field.options.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : field.type === 'textarea' ? (
                <Textarea
                  id={field.key}
                  placeholder={field.placeholder}
                  value={formData[field.key] || ""}
                  onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
                  required={field.required}
                />
              ) : (
                <div className="relative">
                  <Input
                    id={field.key}
                    type={field.type === 'password' && !showPasswords ? 'password' : 'text'}
                    placeholder={field.placeholder}
                    value={formData[field.key] || ""}
                    onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
                    required={field.required}
                  />
                  {field.type === 'password' && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowPasswords(!showPasswords)}
                    >
                      {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  )}
                </div>
              )}
              
              {field.description && (
                <p className="text-xs text-muted-foreground mt-1">{field.description}</p>
              )}
            </div>
          ))}

          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Your API credentials are encrypted and stored securely. 
              We never share your data with third parties.
            </AlertDescription>
          </Alert>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Connecting..." : "Connect Integration"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
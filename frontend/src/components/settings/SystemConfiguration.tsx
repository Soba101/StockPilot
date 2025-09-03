"use client"

import * as React from "react"
import { z } from "zod"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Server, Database, Shield, Zap, AlertTriangle, Info, Save, RotateCcw, Eye, EyeOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/components/ui/toast"

const systemConfigSchema = z.object({
  // Database Configuration
  databaseMaxConnections: z.number().min(1, "Must be at least 1").max(1000, "Must be 1000 or less"),
  databaseConnectionTimeout: z.number().min(1000, "Must be at least 1000ms").max(60000, "Must be 60000ms or less"),
  queryTimeout: z.number().min(1000, "Must be at least 1000ms").max(300000, "Must be 300000ms or less"),
  enableQueryLogging: z.boolean(),
  
  // API Configuration
  apiRateLimit: z.number().min(1, "Must be at least 1").max(10000, "Must be 10000 or less"),
  apiRequestTimeout: z.number().min(1000, "Must be at least 1000ms").max(120000, "Must be 120000ms or less"),
  enableCors: z.boolean(),
  corsOrigins: z.string(),
  
  // Security Configuration
  sessionTimeout: z.number().min(300, "Must be at least 5 minutes").max(86400, "Must be 24 hours or less"),
  passwordMinLength: z.number().min(6, "Must be at least 6").max(128, "Must be 128 or less"),
  enableTwoFactor: z.boolean(),
  enableAuditLogging: z.boolean(),
  
  // Performance Configuration
  enableCaching: z.boolean(),
  cacheTimeout: z.number().min(60, "Must be at least 60 seconds").max(3600, "Must be 3600 seconds or less"),
  maxUploadSize: z.number().min(1, "Must be at least 1MB").max(100, "Must be 100MB or less"),
  
  // Backup Configuration
  enableAutomaticBackups: z.boolean(),
  backupSchedule: z.enum(["hourly", "daily", "weekly"]),
  backupRetentionDays: z.number().min(1, "Must be at least 1 day").max(365, "Must be 365 days or less"),
  
  // Notification Configuration
  enableEmailNotifications: z.boolean(),
  smtpHost: z.string().min(1, "SMTP host is required"),
  smtpPort: z.number().min(1, "Must be at least 1").max(65535, "Must be 65535 or less"),
  smtpUsername: z.string(),
  smtpPassword: z.string(),
  enableSslTls: z.boolean(),
})

type SystemConfigData = z.infer<typeof systemConfigSchema>

interface SystemConfigurationProps {
  className?: string
  initialData?: Partial<SystemConfigData>
  onSave?: (data: SystemConfigData) => Promise<void>
}

const DEFAULT_CONFIG: SystemConfigData = {
  // Database
  databaseMaxConnections: 100,
  databaseConnectionTimeout: 5000,
  queryTimeout: 30000,
  enableQueryLogging: false,
  
  // API
  apiRateLimit: 1000,
  apiRequestTimeout: 30000,
  enableCors: true,
  corsOrigins: "*",
  
  // Security
  sessionTimeout: 3600,
  passwordMinLength: 8,
  enableTwoFactor: false,
  enableAuditLogging: true,
  
  // Performance
  enableCaching: true,
  cacheTimeout: 300,
  maxUploadSize: 10,
  
  // Backup
  enableAutomaticBackups: true,
  backupSchedule: "daily",
  backupRetentionDays: 30,
  
  // Notifications
  enableEmailNotifications: true,
  smtpHost: "",
  smtpPort: 587,
  smtpUsername: "",
  smtpPassword: "",
  enableSslTls: true,
}

export function SystemConfiguration({ className, initialData, onSave }: SystemConfigurationProps) {
  const [isLoading, setIsLoading] = React.useState(false)
  const [showPasswords, setShowPasswords] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState("database")
  const { toast } = useToast()

  const form = useForm<SystemConfigData>({
    resolver: zodResolver(systemConfigSchema),
    defaultValues: { ...DEFAULT_CONFIG, ...initialData },
  })

  const { watch, formState: { isDirty, errors } } = form
  const watchedValues = watch()

  const handleSubmit = async (data: SystemConfigData) => {
    if (!onSave) return

    setIsLoading(true)
    try {
      await onSave(data)
      form.reset(data)
      toast({
        title: "Success",
        description: "System configuration updated successfully",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update system configuration",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    form.reset()
    toast({
      title: "Settings Reset",
      description: "All changes have been discarded",
    })
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <h3 className="text-lg font-medium">System Configuration</h3>
        <p className="text-muted-foreground">
          Configure database, API, security, and performance settings
        </p>
      </div>

      {/* Warning Alert */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <strong>Warning:</strong> Changes to system configuration may affect application performance 
          and require a server restart. Please review carefully before saving.
        </AlertDescription>
      </Alert>

      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="database">Database</TabsTrigger>
            <TabsTrigger value="api">API</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="backup">Backup</TabsTrigger>
          </TabsList>

          {/* Database Configuration */}
          <TabsContent value="database" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Database Settings
                </CardTitle>
                <CardDescription>
                  PostgreSQL connection and query configuration
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="databaseMaxConnections">Max Connections</Label>
                    <Input
                      id="databaseMaxConnections"
                      type="number"
                      min="1"
                      max="1000"
                      {...form.register("databaseMaxConnections", { valueAsNumber: true })}
                    />
                    {errors.databaseMaxConnections && (
                      <p className="text-sm text-red-500 mt-1">{errors.databaseMaxConnections.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="databaseConnectionTimeout">Connection Timeout (ms)</Label>
                    <Input
                      id="databaseConnectionTimeout"
                      type="number"
                      min="1000"
                      max="60000"
                      {...form.register("databaseConnectionTimeout", { valueAsNumber: true })}
                    />
                    {errors.databaseConnectionTimeout && (
                      <p className="text-sm text-red-500 mt-1">{errors.databaseConnectionTimeout.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="queryTimeout">Query Timeout (ms)</Label>
                    <Input
                      id="queryTimeout"
                      type="number"
                      min="1000"
                      max="300000"
                      {...form.register("queryTimeout", { valueAsNumber: true })}
                    />
                    {errors.queryTimeout && (
                      <p className="text-sm text-red-500 mt-1">{errors.queryTimeout.message}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="enableQueryLogging">Query Logging</Label>
                    <p className="text-xs text-muted-foreground">
                      Log all database queries for debugging (impacts performance)
                    </p>
                  </div>
                  <Switch
                    id="enableQueryLogging"
                    checked={watchedValues.enableQueryLogging}
                    onCheckedChange={(checked) => form.setValue("enableQueryLogging", checked, { shouldDirty: true })}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* API Configuration */}
          <TabsContent value="api" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Server className="h-5 w-5" />
                  API Settings
                </CardTitle>
                <CardDescription>
                  REST API rate limiting and CORS configuration
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="apiRateLimit">Rate Limit (requests/hour)</Label>
                    <Input
                      id="apiRateLimit"
                      type="number"
                      min="1"
                      max="10000"
                      {...form.register("apiRateLimit", { valueAsNumber: true })}
                    />
                    {errors.apiRateLimit && (
                      <p className="text-sm text-red-500 mt-1">{errors.apiRateLimit.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="apiRequestTimeout">Request Timeout (ms)</Label>
                    <Input
                      id="apiRequestTimeout"
                      type="number"
                      min="1000"
                      max="120000"
                      {...form.register("apiRequestTimeout", { valueAsNumber: true })}
                    />
                    {errors.apiRequestTimeout && (
                      <p className="text-sm text-red-500 mt-1">{errors.apiRequestTimeout.message}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="enableCors">Enable CORS</Label>
                    <p className="text-xs text-muted-foreground">
                      Allow cross-origin requests from specified domains
                    </p>
                  </div>
                  <Switch
                    id="enableCors"
                    checked={watchedValues.enableCors}
                    onCheckedChange={(checked) => form.setValue("enableCors", checked, { shouldDirty: true })}
                  />
                </div>

                {watchedValues.enableCors && (
                  <div>
                    <Label htmlFor="corsOrigins">Allowed Origins</Label>
                    <Textarea
                      id="corsOrigins"
                      placeholder="https://example.com, https://app.example.com (or * for all)"
                      {...form.register("corsOrigins")}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Comma-separated list of allowed origins, or * for all
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Configuration */}
          <TabsContent value="security" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Security Settings
                </CardTitle>
                <CardDescription>
                  Authentication, authorization, and security policies
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="sessionTimeout">Session Timeout (seconds)</Label>
                    <Input
                      id="sessionTimeout"
                      type="number"
                      min="300"
                      max="86400"
                      {...form.register("sessionTimeout", { valueAsNumber: true })}
                    />
                    {errors.sessionTimeout && (
                      <p className="text-sm text-red-500 mt-1">{errors.sessionTimeout.message}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {Math.floor(watchedValues.sessionTimeout / 60)} minutes
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="passwordMinLength">Minimum Password Length</Label>
                    <Input
                      id="passwordMinLength"
                      type="number"
                      min="6"
                      max="128"
                      {...form.register("passwordMinLength", { valueAsNumber: true })}
                    />
                    {errors.passwordMinLength && (
                      <p className="text-sm text-red-500 mt-1">{errors.passwordMinLength.message}</p>
                    )}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="enableTwoFactor">Two-Factor Authentication</Label>
                      <p className="text-xs text-muted-foreground">
                        Require 2FA for all user accounts
                      </p>
                    </div>
                    <Switch
                      id="enableTwoFactor"
                      checked={watchedValues.enableTwoFactor}
                      onCheckedChange={(checked) => form.setValue("enableTwoFactor", checked, { shouldDirty: true })}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="enableAuditLogging">Audit Logging</Label>
                      <p className="text-xs text-muted-foreground">
                        Log all user actions for compliance and security
                      </p>
                    </div>
                    <Switch
                      id="enableAuditLogging"
                      checked={watchedValues.enableAuditLogging}
                      onCheckedChange={(checked) => form.setValue("enableAuditLogging", checked, { shouldDirty: true })}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Performance Configuration */}
          <TabsContent value="performance" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Performance Settings
                </CardTitle>
                <CardDescription>
                  Caching, timeouts, and resource limits
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="enableCaching">Enable Caching</Label>
                    <p className="text-xs text-muted-foreground">
                      Cache frequently accessed data to improve performance
                    </p>
                  </div>
                  <Switch
                    id="enableCaching"
                    checked={watchedValues.enableCaching}
                    onCheckedChange={(checked) => form.setValue("enableCaching", checked, { shouldDirty: true })}
                  />
                </div>

                {watchedValues.enableCaching && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="cacheTimeout">Cache Timeout (seconds)</Label>
                      <Input
                        id="cacheTimeout"
                        type="number"
                        min="60"
                        max="3600"
                        {...form.register("cacheTimeout", { valueAsNumber: true })}
                      />
                      {errors.cacheTimeout && (
                        <p className="text-sm text-red-500 mt-1">{errors.cacheTimeout.message}</p>
                      )}
                    </div>
                  </div>
                )}

                <div>
                  <Label htmlFor="maxUploadSize">Maximum Upload Size (MB)</Label>
                  <Input
                    id="maxUploadSize"
                    type="number"
                    min="1"
                    max="100"
                    {...form.register("maxUploadSize", { valueAsNumber: true })}
                  />
                  {errors.maxUploadSize && (
                    <p className="text-sm text-red-500 mt-1">{errors.maxUploadSize.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Maximum file size for uploads (logos, documents, etc.)
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Backup Configuration */}
          <TabsContent value="backup" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Backup & Recovery</CardTitle>
                <CardDescription>
                  Automated backup configuration and data retention
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="enableAutomaticBackups">Automatic Backups</Label>
                    <p className="text-xs text-muted-foreground">
                      Automatically backup database and critical files
                    </p>
                  </div>
                  <Switch
                    id="enableAutomaticBackups"
                    checked={watchedValues.enableAutomaticBackups}
                    onCheckedChange={(checked) => form.setValue("enableAutomaticBackups", checked, { shouldDirty: true })}
                  />
                </div>

                {watchedValues.enableAutomaticBackups && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="backupSchedule">Backup Schedule</Label>
                      <Select
                        value={watchedValues.backupSchedule}
                        onValueChange={(value) => form.setValue("backupSchedule", value as any, { shouldDirty: true })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="hourly">Every Hour</SelectItem>
                          <SelectItem value="daily">Daily (2:00 AM)</SelectItem>
                          <SelectItem value="weekly">Weekly (Sunday 2:00 AM)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="backupRetentionDays">Retention Period (Days)</Label>
                      <Input
                        id="backupRetentionDays"
                        type="number"
                        min="1"
                        max="365"
                        {...form.register("backupRetentionDays", { valueAsNumber: true })}
                      />
                      {errors.backupRetentionDays && (
                        <p className="text-sm text-red-500 mt-1">{errors.backupRetentionDays.message}</p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Configuration Status */}
        <Card>
          <CardHeader>
            <CardTitle>Current Configuration Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-green-600">{watchedValues.databaseMaxConnections}</div>
                <div className="text-sm text-muted-foreground">DB Connections</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{watchedValues.apiRateLimit}</div>
                <div className="text-sm text-muted-foreground">API Rate Limit</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{Math.floor(watchedValues.sessionTimeout / 60)}m</div>
                <div className="text-sm text-muted-foreground">Session Timeout</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-orange-600">{watchedValues.maxUploadSize}MB</div>
                <div className="text-sm text-muted-foreground">Max Upload</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={handleReset}
            disabled={!isDirty || isLoading}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset Changes
          </Button>

          <Button
            type="submit"
            disabled={!isDirty || isLoading || Object.keys(errors).length > 0}
          >
            {isLoading ? "Saving..." : "Save Configuration"}
          </Button>
        </div>
      </form>
    </div>
  )
}
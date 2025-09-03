"use client"

import * as React from "react"
import { z } from "zod"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Package, AlertTriangle, Settings, TrendingUp, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useToast } from "@/components/ui/toast"

const inventoryConfigSchema = z.object({
  defaultReorderPoint: z.number().min(0, "Must be 0 or greater").max(10000, "Must be 10,000 or less"),
  defaultSafetyStock: z.number().min(0, "Must be 0 or greater").max(1000, "Must be 1,000 or less"),
  valuationMethod: z.enum(["FIFO", "LIFO", "WAC"], {
    required_error: "Please select a valuation method",
  }),
  lowStockThreshold: z.number().min(0.1, "Must be at least 0.1%").max(50, "Must be 50% or less"),
  autoReorderEnabled: z.boolean(),
  leadTimeDays: z.number().min(1, "Must be at least 1 day").max(365, "Must be 365 days or less"),
  demandForecastDays: z.number().min(7, "Must be at least 7 days").max(365, "Must be 365 days or less"),
  stockoutRiskThreshold: z.number().min(1, "Must be at least 1%").max(50, "Must be 50% or less"),
  seasonalityEnabled: z.boolean(),
  movementHistoryDays: z.number().min(30, "Must be at least 30 days").max(1095, "Must be 3 years or less"),
})

type InventoryConfigData = z.infer<typeof inventoryConfigSchema>

interface InventorySettingsProps {
  className?: string
  initialData?: Partial<InventoryConfigData>
  onSave?: (data: InventoryConfigData) => Promise<void>
}

const DEFAULT_CONFIG: InventoryConfigData = {
  defaultReorderPoint: 10,
  defaultSafetyStock: 5,
  valuationMethod: "FIFO",
  lowStockThreshold: 10.0,
  autoReorderEnabled: false,
  leadTimeDays: 7,
  demandForecastDays: 30,
  stockoutRiskThreshold: 15.0,
  seasonalityEnabled: true,
  movementHistoryDays: 90,
}

export function InventorySettings({ className, initialData, onSave }: InventorySettingsProps) {
  const [isLoading, setIsLoading] = React.useState(false)
  const { toast } = useToast()

  const form = useForm<InventoryConfigData>({
    resolver: zodResolver(inventoryConfigSchema),
    defaultValues: { ...DEFAULT_CONFIG, ...initialData },
  })

  const { watch, formState: { isDirty, errors } } = form

  // Watch form values for real-time updates
  const watchedValues = watch()

  const handleSubmit = async (data: InventoryConfigData) => {
    if (!onSave) return

    setIsLoading(true)
    try {
      await onSave(data)
      form.reset(data) // Reset form to mark as clean
      toast({
        title: "Success",
        description: "Inventory settings updated successfully",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update inventory settings",
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
        <h3 className="text-lg font-medium">Inventory Configuration</h3>
        <p className="text-muted-foreground">
          Configure default stock levels, reorder rules, and inventory policies
        </p>
      </div>

      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        {/* Stock Level Defaults */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Stock Level Defaults
            </CardTitle>
            <CardDescription>
              Default values for new products and automatic calculations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="defaultReorderPoint">Default Reorder Point</Label>
                <Input
                  id="defaultReorderPoint"
                  type="number"
                  min="0"
                  max="10000"
                  {...form.register("defaultReorderPoint", { valueAsNumber: true })}
                />
                {errors.defaultReorderPoint && (
                  <p className="text-sm text-red-500 mt-1">{errors.defaultReorderPoint.message}</p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  Quantity level that triggers reorder suggestions
                </p>
              </div>

              <div>
                <Label htmlFor="defaultSafetyStock">Default Safety Stock</Label>
                <Input
                  id="defaultSafetyStock"
                  type="number"
                  min="0"
                  max="1000"
                  {...form.register("defaultSafetyStock", { valueAsNumber: true })}
                />
                {errors.defaultSafetyStock && (
                  <p className="text-sm text-red-500 mt-1">{errors.defaultSafetyStock.message}</p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  Buffer stock to handle unexpected demand
                </p>
              </div>

              <div>
                <Label htmlFor="leadTimeDays">Default Lead Time (Days)</Label>
                <Input
                  id="leadTimeDays"
                  type="number"
                  min="1"
                  max="365"
                  {...form.register("leadTimeDays", { valueAsNumber: true })}
                />
                {errors.leadTimeDays && (
                  <p className="text-sm text-red-500 mt-1">{errors.leadTimeDays.message}</p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  Time from order placement to receipt
                </p>
              </div>

              <div>
                <Label htmlFor="lowStockThreshold">Low Stock Threshold (%)</Label>
                <Input
                  id="lowStockThreshold"
                  type="number"
                  min="0.1"
                  max="50"
                  step="0.1"
                  {...form.register("lowStockThreshold", { valueAsNumber: true })}
                />
                {errors.lowStockThreshold && (
                  <p className="text-sm text-red-500 mt-1">{errors.lowStockThreshold.message}</p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  Percentage of reorder point that triggers low stock alerts
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Valuation & Costing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Valuation & Costing
            </CardTitle>
            <CardDescription>
              How inventory values are calculated for financial reporting
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="valuationMethod">Inventory Valuation Method</Label>
              <Select
                value={watchedValues.valuationMethod}
                onValueChange={(value) => form.setValue("valuationMethod", value as any, { shouldDirty: true })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select valuation method" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="FIFO">
                    <div>
                      <div className="font-medium">FIFO (First In, First Out)</div>
                      <div className="text-xs text-muted-foreground">
                        Oldest inventory costs are used first
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="LIFO">
                    <div>
                      <div className="font-medium">LIFO (Last In, First Out)</div>
                      <div className="text-xs text-muted-foreground">
                        Newest inventory costs are used first
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="WAC">
                    <div>
                      <div className="font-medium">WAC (Weighted Average Cost)</div>
                      <div className="text-xs text-muted-foreground">
                        Average cost across all inventory
                      </div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              {errors.valuationMethod && (
                <p className="text-sm text-red-500 mt-1">{errors.valuationMethod.message}</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Automation & Forecasting */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Automation & Forecasting
            </CardTitle>
            <CardDescription>
              Configure automated processes and demand forecasting
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Auto-reorder Settings */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="autoReorderEnabled">Automatic Reordering</Label>
                  <p className="text-xs text-muted-foreground">
                    Automatically generate purchase orders when stock levels are low
                  </p>
                </div>
                <Switch
                  id="autoReorderEnabled"
                  checked={watchedValues.autoReorderEnabled}
                  onCheckedChange={(checked) => form.setValue("autoReorderEnabled", checked, { shouldDirty: true })}
                />
              </div>

              {watchedValues.autoReorderEnabled && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Automatic reordering will create draft purchase orders that require approval before processing.
                  </AlertDescription>
                </Alert>
              )}
            </div>

            <Separator />

            {/* Forecasting Settings */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="demandForecastDays">Demand Forecast Period (Days)</Label>
                  <Input
                    id="demandForecastDays"
                    type="number"
                    min="7"
                    max="365"
                    {...form.register("demandForecastDays", { valueAsNumber: true })}
                  />
                  {errors.demandForecastDays && (
                    <p className="text-sm text-red-500 mt-1">{errors.demandForecastDays.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    How far ahead to predict demand
                  </p>
                </div>

                <div>
                  <Label htmlFor="movementHistoryDays">Historical Data Period (Days)</Label>
                  <Input
                    id="movementHistoryDays"
                    type="number"
                    min="30"
                    max="1095"
                    {...form.register("movementHistoryDays", { valueAsNumber: true })}
                  />
                  {errors.movementHistoryDays && (
                    <p className="text-sm text-red-500 mt-1">{errors.movementHistoryDays.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Amount of historical data to use for forecasting
                  </p>
                </div>

                <div>
                  <Label htmlFor="stockoutRiskThreshold">Stockout Risk Threshold (%)</Label>
                  <Input
                    id="stockoutRiskThreshold"
                    type="number"
                    min="1"
                    max="50"
                    step="0.1"
                    {...form.register("stockoutRiskThreshold", { valueAsNumber: true })}
                  />
                  {errors.stockoutRiskThreshold && (
                    <p className="text-sm text-red-500 mt-1">{errors.stockoutRiskThreshold.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Risk percentage that triggers stockout warnings
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="seasonalityEnabled">Seasonal Demand Patterns</Label>
                  <p className="text-xs text-muted-foreground">
                    Include seasonal trends in demand forecasting
                  </p>
                </div>
                <Switch
                  id="seasonalityEnabled"
                  checked={watchedValues.seasonalityEnabled}
                  onCheckedChange={(checked) => form.setValue("seasonalityEnabled", checked, { shouldDirty: true })}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Current Configuration Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration Summary</CardTitle>
            <CardDescription>
              Preview of current inventory management settings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div className="space-y-2">
                <div className="font-medium text-muted-foreground">Stock Levels</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Reorder Point:</span>
                    <span className="font-medium">{watchedValues.defaultReorderPoint} units</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Safety Stock:</span>
                    <span className="font-medium">{watchedValues.defaultSafetyStock} units</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Lead Time:</span>
                    <span className="font-medium">{watchedValues.leadTimeDays} days</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="font-medium text-muted-foreground">Valuation & Alerts</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Method:</span>
                    <span className="font-medium">{watchedValues.valuationMethod}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Low Stock:</span>
                    <span className="font-medium">{watchedValues.lowStockThreshold}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Stockout Risk:</span>
                    <span className="font-medium">{watchedValues.stockoutRiskThreshold}%</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="font-medium text-muted-foreground">Automation & Forecasting</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Auto Reorder:</span>
                    <span className="font-medium">
                      {watchedValues.autoReorderEnabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Seasonality:</span>
                    <span className="font-medium">
                      {watchedValues.seasonalityEnabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Forecast Period:</span>
                    <span className="font-medium">{watchedValues.demandForecastDays} days</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Important Notes */}
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>Important:</strong> Changes to inventory configuration will affect all new products. 
            Existing products retain their current settings unless manually updated.
          </AlertDescription>
        </Alert>

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
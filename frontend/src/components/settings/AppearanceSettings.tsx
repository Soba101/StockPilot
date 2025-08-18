"use client"

import * as React from "react"
import { z } from "zod"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Palette, Monitor, Sun, Moon, Smartphone, Layout, Type, Save, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/components/ui/toast"

const appearanceConfigSchema = z.object({
  theme: z.enum(["light", "dark", "system"]),
  primaryColor: z.enum(["blue", "green", "purple", "orange", "red", "pink"]),
  fontSize: z.enum(["small", "medium", "large"]),
  density: z.enum(["compact", "comfortable", "spacious"]),
  sidebarCollapsed: z.boolean(),
  showAnimations: z.boolean(),
  highContrast: z.boolean(),
  reducedMotion: z.boolean(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]),
  timeFormat: z.enum(["12h", "24h"]),
  currency: z.string().min(1, "Currency is required"),
  language: z.enum(["en", "es", "fr", "de", "pt"]),
  timezone: z.string().min(1, "Timezone is required"),
})

type AppearanceConfigData = z.infer<typeof appearanceConfigSchema>

interface AppearanceSettingsProps {
  className?: string
  initialData?: Partial<AppearanceConfigData>
  onSave?: (data: AppearanceConfigData) => Promise<void>
}

const DEFAULT_CONFIG: AppearanceConfigData = {
  theme: "system",
  primaryColor: "blue",
  fontSize: "medium",
  density: "comfortable",
  sidebarCollapsed: false,
  showAnimations: true,
  highContrast: false,
  reducedMotion: false,
  dateFormat: "MM/DD/YYYY",
  timeFormat: "12h",
  currency: "USD",
  language: "en",
  timezone: "America/New_York",
}

const COLOR_OPTIONS = [
  { value: "blue", label: "Blue", class: "bg-blue-500" },
  { value: "green", label: "Green", class: "bg-green-500" },
  { value: "purple", label: "Purple", class: "bg-purple-500" },
  { value: "orange", label: "Orange", class: "bg-orange-500" },
  { value: "red", label: "Red", class: "bg-red-500" },
  { value: "pink", label: "Pink", class: "bg-pink-500" },
]

export function AppearanceSettings({ className, initialData, onSave }: AppearanceSettingsProps) {
  const [isLoading, setIsLoading] = React.useState(false)
  const { toast } = useToast()

  const form = useForm<AppearanceConfigData>({
    resolver: zodResolver(appearanceConfigSchema),
    defaultValues: { ...DEFAULT_CONFIG, ...initialData },
  })

  const { watch, formState: { isDirty, errors } } = form
  const watchedValues = watch()

  const handleSubmit = async (data: AppearanceConfigData) => {
    if (!onSave) return

    setIsLoading(true)
    try {
      await onSave(data)
      form.reset(data)
      toast({
        title: "Success",
        description: "Appearance settings updated successfully",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update appearance settings",
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
        <h3 className="text-lg font-medium">Appearance Settings</h3>
        <p className="text-muted-foreground">
          Customize the look and feel of your StockPilot interface
        </p>
      </div>

      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <Tabs defaultValue="theme" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="theme">Theme</TabsTrigger>
            <TabsTrigger value="layout">Layout</TabsTrigger>
            <TabsTrigger value="accessibility">Accessibility</TabsTrigger>
            <TabsTrigger value="localization">Localization</TabsTrigger>
          </TabsList>

          {/* Theme Settings */}
          <TabsContent value="theme" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  Theme & Colors
                </CardTitle>
                <CardDescription>
                  Choose your preferred color scheme and theme
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Theme Mode */}
                <div>
                  <Label className="text-base font-medium">Theme Mode</Label>
                  <RadioGroup
                    value={watchedValues.theme}
                    onValueChange={(value) => form.setValue("theme", value as any, { shouldDirty: true })}
                    className="flex gap-6 mt-3"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="light" id="light" />
                      <Label htmlFor="light" className="flex items-center gap-2 cursor-pointer">
                        <Sun className="h-4 w-4" />
                        Light
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="dark" id="dark" />
                      <Label htmlFor="dark" className="flex items-center gap-2 cursor-pointer">
                        <Moon className="h-4 w-4" />
                        Dark
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="system" id="system" />
                      <Label htmlFor="system" className="flex items-center gap-2 cursor-pointer">
                        <Monitor className="h-4 w-4" />
                        System
                      </Label>
                    </div>
                  </RadioGroup>
                </div>

                {/* Primary Color */}
                <div>
                  <Label className="text-base font-medium">Primary Color</Label>
                  <div className="grid grid-cols-3 gap-3 mt-3">
                    {COLOR_OPTIONS.map((color) => (
                      <button
                        key={color.value}
                        type="button"
                        className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-colors ${
                          watchedValues.primaryColor === color.value 
                            ? 'border-primary bg-primary/5' 
                            : 'border-border hover:border-primary/50'
                        }`}
                        onClick={() => form.setValue("primaryColor", color.value as any, { shouldDirty: true })}
                      >
                        <div className={`w-4 h-4 rounded-full ${color.class}`} />
                        <span className="font-medium">{color.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Layout Settings */}
          <TabsContent value="layout" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layout className="h-5 w-5" />
                  Layout & Navigation
                </CardTitle>
                <CardDescription>
                  Customize the layout and navigation preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Font Size */}
                <div>
                  <Label className="text-base font-medium">Font Size</Label>
                  <RadioGroup
                    value={watchedValues.fontSize}
                    onValueChange={(value) => form.setValue("fontSize", value as any, { shouldDirty: true })}
                    className="flex gap-6 mt-3"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="small" id="font-small" />
                      <Label htmlFor="font-small" className="cursor-pointer text-sm">Small</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="medium" id="font-medium" />
                      <Label htmlFor="font-medium" className="cursor-pointer">Medium</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="large" id="font-large" />
                      <Label htmlFor="font-large" className="cursor-pointer text-lg">Large</Label>
                    </div>
                  </RadioGroup>
                </div>

                {/* Density */}
                <div>
                  <Label className="text-base font-medium">Interface Density</Label>
                  <RadioGroup
                    value={watchedValues.density}
                    onValueChange={(value) => form.setValue("density", value as any, { shouldDirty: true })}
                    className="flex gap-6 mt-3"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="compact" id="compact" />
                      <Label htmlFor="compact" className="cursor-pointer">Compact</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="comfortable" id="comfortable" />
                      <Label htmlFor="comfortable" className="cursor-pointer">Comfortable</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="spacious" id="spacious" />
                      <Label htmlFor="spacious" className="cursor-pointer">Spacious</Label>
                    </div>
                  </RadioGroup>
                </div>

                {/* Sidebar */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="sidebarCollapsed">Collapsed Sidebar by Default</Label>
                    <p className="text-xs text-muted-foreground">
                      Start with sidebar collapsed to maximize content space
                    </p>
                  </div>
                  <Switch
                    id="sidebarCollapsed"
                    checked={watchedValues.sidebarCollapsed}
                    onCheckedChange={(checked) => form.setValue("sidebarCollapsed", checked, { shouldDirty: true })}
                  />
                </div>

                {/* Animations */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="showAnimations">Enable Animations</Label>
                    <p className="text-xs text-muted-foreground">
                      Show smooth transitions and loading animations
                    </p>
                  </div>
                  <Switch
                    id="showAnimations"
                    checked={watchedValues.showAnimations}
                    onCheckedChange={(checked) => form.setValue("showAnimations", checked, { shouldDirty: true })}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Accessibility Settings */}
          <TabsContent value="accessibility" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Accessibility Options</CardTitle>
                <CardDescription>
                  Configure accessibility features for better usability
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="highContrast">High Contrast Mode</Label>
                    <p className="text-xs text-muted-foreground">
                      Increase contrast for better visibility
                    </p>
                  </div>
                  <Switch
                    id="highContrast"
                    checked={watchedValues.highContrast}
                    onCheckedChange={(checked) => form.setValue("highContrast", checked, { shouldDirty: true })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="reducedMotion">Reduced Motion</Label>
                    <p className="text-xs text-muted-foreground">
                      Minimize animations for motion sensitivity
                    </p>
                  </div>
                  <Switch
                    id="reducedMotion"
                    checked={watchedValues.reducedMotion}
                    onCheckedChange={(checked) => form.setValue("reducedMotion", checked, { shouldDirty: true })}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Localization Settings */}
          <TabsContent value="localization" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Type className="h-5 w-5" />
                  Localization
                </CardTitle>
                <CardDescription>
                  Configure language, date, time, and currency formats
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="language">Language</Label>
                    <Select
                      value={watchedValues.language}
                      onValueChange={(value) => form.setValue("language", value as any, { shouldDirty: true })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="es">Español</SelectItem>
                        <SelectItem value="fr">Français</SelectItem>
                        <SelectItem value="de">Deutsch</SelectItem>
                        <SelectItem value="pt">Português</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="timezone">Timezone</Label>
                    <Select
                      value={watchedValues.timezone}
                      onValueChange={(value) => form.setValue("timezone", value, { shouldDirty: true })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="America/New_York">Eastern Time (EST/EDT)</SelectItem>
                        <SelectItem value="America/Chicago">Central Time (CST/CDT)</SelectItem>
                        <SelectItem value="America/Denver">Mountain Time (MST/MDT)</SelectItem>
                        <SelectItem value="America/Los_Angeles">Pacific Time (PST/PDT)</SelectItem>
                        <SelectItem value="Europe/London">London (GMT/BST)</SelectItem>
                        <SelectItem value="Europe/Paris">Paris (CET/CEST)</SelectItem>
                        <SelectItem value="Asia/Tokyo">Tokyo (JST)</SelectItem>
                        <SelectItem value="UTC">UTC</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="dateFormat">Date Format</Label>
                    <Select
                      value={watchedValues.dateFormat}
                      onValueChange={(value) => form.setValue("dateFormat", value as any, { shouldDirty: true })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="MM/DD/YYYY">MM/DD/YYYY (US)</SelectItem>
                        <SelectItem value="DD/MM/YYYY">DD/MM/YYYY (EU)</SelectItem>
                        <SelectItem value="YYYY-MM-DD">YYYY-MM-DD (ISO)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="timeFormat">Time Format</Label>
                    <Select
                      value={watchedValues.timeFormat}
                      onValueChange={(value) => form.setValue("timeFormat", value as any, { shouldDirty: true })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="12h">12-hour (AM/PM)</SelectItem>
                        <SelectItem value="24h">24-hour</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="currency">Currency</Label>
                    <Select
                      value={watchedValues.currency}
                      onValueChange={(value) => form.setValue("currency", value, { shouldDirty: true })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="USD">USD ($)</SelectItem>
                        <SelectItem value="EUR">EUR (€)</SelectItem>
                        <SelectItem value="GBP">GBP (£)</SelectItem>
                        <SelectItem value="CAD">CAD (C$)</SelectItem>
                        <SelectItem value="AUD">AUD (A$)</SelectItem>
                        <SelectItem value="JPY">JPY (¥)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Preview Section */}
        <Card>
          <CardHeader>
            <CardTitle>Preview</CardTitle>
            <CardDescription>
              See how your settings will look
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="font-medium text-muted-foreground">Theme & Layout</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Theme:</span>
                    <span className="font-medium capitalize">{watchedValues.theme}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Primary Color:</span>
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${COLOR_OPTIONS.find(c => c.value === watchedValues.primaryColor)?.class}`} />
                      <span className="font-medium capitalize">{watchedValues.primaryColor}</span>
                    </div>
                  </div>
                  <div className="flex justify-between">
                    <span>Font Size:</span>
                    <span className="font-medium capitalize">{watchedValues.fontSize}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Density:</span>
                    <span className="font-medium capitalize">{watchedValues.density}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="font-medium text-muted-foreground">Localization</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Language:</span>
                    <span className="font-medium">{watchedValues.language.toUpperCase()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Date Format:</span>
                    <span className="font-medium">{watchedValues.dateFormat}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Time Format:</span>
                    <span className="font-medium">{watchedValues.timeFormat === '12h' ? '12-hour' : '24-hour'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Currency:</span>
                    <span className="font-medium">{watchedValues.currency}</span>
                  </div>
                </div>
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
            {isLoading ? "Saving..." : "Save Preferences"}
          </Button>
        </div>
      </form>
    </div>
  )
}
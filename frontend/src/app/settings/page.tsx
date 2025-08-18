'use client'

import * as React from 'react'
import { SettingsLayout, defaultSettingsSections } from '@/components/settings/SettingsLayout'
import { OrganizationSettings } from '@/components/settings/OrganizationSettings'
import { UserManagement } from '@/components/settings/UserManagement'
import { PermissionMatrix } from '@/components/settings/PermissionMatrix'
import { InventorySettings } from '@/components/settings/InventorySettings'
import { SystemConfiguration } from '@/components/settings/SystemConfiguration'
import { IntegrationSettings } from '@/components/settings/IntegrationSettings'
import { AppearanceSettings } from '@/components/settings/AppearanceSettings'

export default function SettingsPage() {
  const [currentSection, setCurrentSection] = React.useState('organization')
  const [saveStatus, setSaveStatus] = React.useState<"idle" | "saving" | "saved" | "error">("idle")
  const [lastSaved, setLastSaved] = React.useState<Date>()

  const handleSectionChange = (section: string) => {
    setCurrentSection(section)
  }

  const handleOrganizationSave = async (data: unknown) => {
    setSaveStatus("saving")
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      console.log('Saving organization data:', data)
      setSaveStatus("saved")
      setLastSaved(new Date())
    } catch (error) {
      setSaveStatus("error")
      throw error
    }
  }

  const handleInventorySave = async (data: unknown) => {
    setSaveStatus("saving")
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      console.log('Saving inventory configuration:', data)
      setSaveStatus("saved")
      setLastSaved(new Date())
    } catch (error) {
      setSaveStatus("error")
      throw error
    }
  }

  const handleSystemSave = async (data: unknown) => {
    setSaveStatus("saving")
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      console.log('Saving system configuration:', data)
      setSaveStatus("saved")
      setLastSaved(new Date())
    } catch (error) {
      setSaveStatus("error")
      throw error
    }
  }

  const handleAppearanceSave = async (data: unknown) => {
    setSaveStatus("saving")
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      console.log('Saving appearance settings:', data)
      setSaveStatus("saved")
      setLastSaved(new Date())
    } catch (error) {
      setSaveStatus("error")
      throw error
    }
  }

  const renderCurrentSection = () => {
    switch (currentSection) {
      case 'organization':
        return (
          <OrganizationSettings
            initialData={{
              name: 'Demo Company',
              displayName: 'Demo Company Inc.',
              description: 'A demo inventory management company',
              email: 'contact@democompany.com',
              phone: '+1 (555) 123-4567',
              website: 'https://www.democompany.com',
            }}
            onSave={handleOrganizationSave}
          />
        )
      case 'users':
        return <UserManagement />
      case 'permissions':
        return <PermissionMatrix />
      case 'inventory':
        return (
          <InventorySettings
            initialData={{
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
            }}
            onSave={handleInventorySave}
          />
        )
      case 'system':
        return (
          <SystemConfiguration
            initialData={{
              databaseMaxConnections: 100,
              databaseConnectionTimeout: 5000,
              queryTimeout: 30000,
              enableQueryLogging: false,
              apiRateLimit: 1000,
              apiRequestTimeout: 30000,
              enableCors: true,
              corsOrigins: "*",
              sessionTimeout: 3600,
              passwordMinLength: 8,
              enableTwoFactor: false,
              enableAuditLogging: true,
              enableCaching: true,
              cacheTimeout: 300,
              maxUploadSize: 10,
              enableAutomaticBackups: true,
              backupSchedule: "daily",
              backupRetentionDays: 30,
              enableEmailNotifications: true,
              smtpHost: "",
              smtpPort: 587,
              smtpUsername: "",
              smtpPassword: "",
              enableSslTls: true,
            }}
            onSave={handleSystemSave}
          />
        )
      case 'integrations':
        return <IntegrationSettings />
      case 'appearance':
        return (
          <AppearanceSettings
            initialData={{
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
            }}
            onSave={handleAppearanceSave}
          />
        )
      default:
        return (
          <div className="p-8 border-2 border-dashed border-border rounded-lg text-center">
            <p className="text-muted-foreground">Section not found</p>
          </div>
        )
    }
  }

  return (
    <SettingsLayout
      currentSection={currentSection}
      onSectionChange={handleSectionChange}
      sections={defaultSettingsSections}
      saveStatus={saveStatus}
      lastSaved={lastSaved}
    >
      {renderCurrentSection()}
    </SettingsLayout>
  )
}



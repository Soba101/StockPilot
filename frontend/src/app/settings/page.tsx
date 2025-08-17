'use client'

import * as React from 'react'
import { SettingsLayout, defaultSettingsSections } from '@/components/settings/SettingsLayout'
import { OrganizationSettings } from '@/components/settings/OrganizationSettings'

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
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium">User Management</h3>
              <p className="text-muted-foreground">Manage team members and their access levels.</p>
            </div>
            <div className="p-8 border-2 border-dashed border-border rounded-lg text-center">
              <p className="text-muted-foreground">User management interface coming soon...</p>
            </div>
          </div>
        )
      case 'permissions':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium">Roles & Permissions</h3>
              <p className="text-muted-foreground">Configure user roles and access control.</p>
            </div>
            <div className="p-8 border-2 border-dashed border-border rounded-lg text-center">
              <p className="text-muted-foreground">Permission matrix coming soon...</p>
            </div>
          </div>
        )
      case 'inventory':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium">Inventory Settings</h3>
              <p className="text-muted-foreground">Configure default stock levels and reorder rules.</p>
            </div>
            <div className="p-8 border-2 border-dashed border-border rounded-lg text-center">
              <p className="text-muted-foreground">Inventory configuration coming soon...</p>
            </div>
          </div>
        )
      case 'system':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium">System Configuration</h3>
              <p className="text-muted-foreground">Database, API, and performance settings.</p>
            </div>
            <div className="p-8 border-2 border-dashed border-border rounded-lg text-center">
              <p className="text-muted-foreground">System configuration coming soon...</p>
            </div>
          </div>
        )
      case 'integrations':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium">Integrations</h3>
              <p className="text-muted-foreground">Third-party services and webhook configuration.</p>
            </div>
            <div className="p-8 border-2 border-dashed border-border rounded-lg text-center">
              <p className="text-muted-foreground">Integration settings coming soon...</p>
            </div>
          </div>
        )
      case 'appearance':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium">Appearance</h3>
              <p className="text-muted-foreground">Customize theme, layout, and personalization options.</p>
            </div>
            <div className="p-8 border-2 border-dashed border-border rounded-lg text-center">
              <p className="text-muted-foreground">Appearance settings coming soon...</p>
            </div>
          </div>
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



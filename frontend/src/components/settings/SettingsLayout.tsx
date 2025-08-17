"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  Settings, 
  Building2, 
  Users, 
  Shield, 
  Package, 
  Server, 
  Palette, 
  Plug,
  ChevronRight,
  Save,
  Loader2
} from "lucide-react"

export interface SettingsSection {
  id: string
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  component: React.ComponentType
  permissions?: string[]
  badge?: string
  disabled?: boolean
}

export interface SettingsLayoutProps {
  children: React.ReactNode
  currentSection: string
  onSectionChange: (section: string) => void
  sections: SettingsSection[]
  title?: string
  description?: string
  autoSave?: boolean
  saveStatus?: "idle" | "saving" | "saved" | "error"
  lastSaved?: Date
}

export const defaultSettingsSections: SettingsSection[] = [
  {
    id: "organization",
    title: "Organization",
    description: "Company profile and basic information",
    icon: Building2,
    component: () => <div>Organization Settings</div>,
  },
  {
    id: "users",
    title: "User Management",
    description: "Manage team members and their access",
    icon: Users,
    component: () => <div>User Management</div>,
    permissions: ["settings:users:read"],
  },
  {
    id: "permissions",
    title: "Roles & Permissions",
    description: "Configure user roles and access control",
    icon: Shield,
    component: () => <div>Permissions</div>,
    permissions: ["settings:permissions:read"],
    badge: "Admin",
  },
  {
    id: "inventory",
    title: "Inventory Settings",
    description: "Default stock levels and reorder rules",
    icon: Package,
    component: () => <div>Inventory Settings</div>,
  },
  {
    id: "system",
    title: "System Configuration",
    description: "Database, API, and performance settings",
    icon: Server,
    component: () => <div>System Configuration</div>,
    permissions: ["settings:system:read"],
    badge: "Advanced",
  },
  {
    id: "integrations",
    title: "Integrations",
    description: "Third-party services and webhooks",
    icon: Plug,
    component: () => <div>Integrations</div>,
  },
  {
    id: "appearance",
    title: "Appearance",
    description: "Theme, layout, and personalization",
    icon: Palette,
    component: () => <div>Appearance Settings</div>,
  },
]

export function SettingsLayout({
  children,
  currentSection,
  onSectionChange,
  sections = defaultSettingsSections,
  title = "Settings",
  description = "Manage your workspace configuration",
  autoSave = true,
  saveStatus = "idle",
  lastSaved,
}: SettingsLayoutProps) {
  const currentSectionData = sections.find(s => s.id === currentSection)
  
  const getSaveStatusMessage = () => {
    switch (saveStatus) {
      case "saving":
        return "Saving..."
      case "saved":
        return lastSaved ? `Saved ${formatTimeAgo(lastSaved)}` : "Saved"
      case "error":
        return "Error saving"
      default:
        return ""
    }
  }

  const getSaveStatusIcon = () => {
    switch (saveStatus) {
      case "saving":
        return <Loader2 className="h-3 w-3 animate-spin" />
      case "saved":
        return <Save className="h-3 w-3 text-green-600" />
      case "error":
        return <Save className="h-3 w-3 text-red-600" />
      default:
        return null
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Settings className="h-8 w-8" />
              {title}
            </h1>
            <p className="text-muted-foreground mt-1">{description}</p>
          </div>
          
          {/* Auto-save status */}
          {autoSave && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {getSaveStatusIcon()}
              <span>{getSaveStatusMessage()}</span>
            </div>
          )}
        </div>

        {/* Breadcrumb */}
        {currentSectionData && (
          <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
            <span>Settings</span>
            <ChevronRight className="h-4 w-4" />
            <span className="text-foreground font-medium">
              {currentSectionData.title}
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar Navigation */}
        <div className="lg:col-span-1">
          <Card>
            <CardContent className="p-0">
              <div className="p-4">
                <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                  Configuration
                </h3>
              </div>
              <Separator />
              <nav className="p-2">
                {sections.map((section) => {
                  const isActive = currentSection === section.id
                  const Icon = section.icon
                  
                  return (
                    <button
                      key={section.id}
                      onClick={() => onSectionChange(section.id)}
                      disabled={section.disabled}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 text-left text-sm rounded-md transition-colors",
                        "hover:bg-accent hover:text-accent-foreground",
                        "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                        isActive && "bg-accent text-accent-foreground font-medium"
                      )}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="truncate">{section.title}</span>
                          {section.badge && (
                            <Badge variant="secondary" className="ml-2 text-xs">
                              {section.badge}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {section.description}
                        </p>
                      </div>
                    </button>
                  )
                })}
              </nav>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3">
          <Card>
            <CardContent className="p-6">
              {/* Section Header */}
              {currentSectionData && (
                <div className="mb-6">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <currentSectionData.icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold">
                        {currentSectionData.title}
                      </h2>
                      <p className="text-muted-foreground text-sm">
                        {currentSectionData.description}
                      </p>
                    </div>
                  </div>
                  <Separator />
                </div>
              )}
              
              {/* Dynamic Content */}
              {children}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

// Helper function to format time ago
function formatTimeAgo(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (seconds < 60) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return date.toLocaleDateString()
}
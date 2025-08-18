"use client"

import * as React from "react"
import { z } from "zod"
import { Shield, AlertTriangle, Info, Save, RotateCcw, Search, Filter } from "lucide-react"
import { useRoles, usePermissionsByCategory, useUpdateRole, type Role, type Permission } from "@/hooks/use-roles"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import { useToast } from "@/components/ui/toast"

interface PermissionMatrixProps {
  className?: string
}

interface PermissionChange {
  roleId: string
  permissionId: string
  granted: boolean
}

export function PermissionMatrix({ className }: PermissionMatrixProps) {
  const [searchTerm, setSearchTerm] = React.useState("")
  const [categoryFilter, setCategoryFilter] = React.useState<string>("all")
  const [riskFilter, setRiskFilter] = React.useState<string>("all")
  const [pendingChanges, setPendingChanges] = React.useState<Map<string, PermissionChange>>(new Map())
  const [expandedCategories, setExpandedCategories] = React.useState<Set<string>>(new Set())

  // Hooks
  const { data: roles = [], isLoading: rolesLoading, error: rolesError } = useRoles()
  const { data: permissionsByCategory = {}, isLoading: permissionsLoading, error: permissionsError } = usePermissionsByCategory()
  const updateRole = useUpdateRole()
  const { toast } = useToast()

  // Filter permissions by search and filters
  const filteredCategories = React.useMemo(() => {
    const categories = Object.keys(permissionsByCategory)
    
    return categories.reduce((acc, category) => {
      const categoryPermissions = permissionsByCategory[category]
      
      const filtered = categoryPermissions.filter((permission: Permission) => {
        const matchesSearch = searchTerm === "" || 
          permission.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          permission.description.toLowerCase().includes(searchTerm.toLowerCase())
        
        const matchesRisk = riskFilter === "all" || permission.riskLevel === riskFilter
        
        return matchesSearch && matchesRisk
      })
      
      if (filtered.length > 0 && (categoryFilter === "all" || category === categoryFilter)) {
        acc[category] = filtered
      }
      
      return acc
    }, {} as Record<string, Permission[]>)
  }, [permissionsByCategory, searchTerm, categoryFilter, riskFilter])

  // Get unique categories for filter
  const categories = Object.keys(permissionsByCategory)

  // Initialize expanded categories
  React.useEffect(() => {
    if (categories.length > 0 && expandedCategories.size === 0) {
      setExpandedCategories(new Set(categories.slice(0, 2))) // Expand first 2 by default
    }
  }, [categories, expandedCategories.size])

  // Handle permission change
  const handlePermissionChange = (roleId: string, permissionId: string, granted: boolean) => {
    const role = roles.find(r => r.id === roleId)
    if (!role || role.isSystem) return

    const changeKey = `${roleId}-${permissionId}`
    const newChanges = new Map(pendingChanges)
    
    newChanges.set(changeKey, {
      roleId,
      permissionId,
      granted,
    })
    
    setPendingChanges(newChanges)
  }

  // Check if role has permission (considering pending changes)
  const hasPermission = (roleId: string, permissionId: string): boolean => {
    const changeKey = `${roleId}-${permissionId}`
    const pendingChange = pendingChanges.get(changeKey)
    
    if (pendingChange) {
      return pendingChange.granted
    }
    
    const role = roles.find(r => r.id === roleId)
    return role?.permissions.includes(permissionId) || false
  }

  // Save all pending changes
  const handleSaveChanges = async () => {
    if (pendingChanges.size === 0) return

    try {
      // Group changes by role
      const changesByRole = new Map<string, string[]>()
      
      pendingChanges.forEach((change) => {
        const role = roles.find(r => r.id === change.roleId)
        if (!role) return
        
        let currentPermissions = [...role.permissions]
        
        if (!changesByRole.has(change.roleId)) {
          changesByRole.set(change.roleId, currentPermissions)
        }
        
        const permissions = changesByRole.get(change.roleId)!
        
        if (change.granted) {
          if (!permissions.includes(change.permissionId)) {
            permissions.push(change.permissionId)
          }
        } else {
          const index = permissions.indexOf(change.permissionId)
          if (index > -1) {
            permissions.splice(index, 1)
          }
        }
        
        changesByRole.set(change.roleId, permissions)
      })

      // Apply all role updates
      const updatePromises = Array.from(changesByRole.entries()).map(([roleId, permissions]) => 
        updateRole.mutateAsync({ id: roleId, data: { permissions } })
      )

      await Promise.all(updatePromises)

      setPendingChanges(new Map())
      toast({
        title: "Success",
        description: `Updated permissions for ${changesByRole.size} role${changesByRole.size > 1 ? 's' : ''}`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update permissions",
        variant: "destructive",
      })
    }
  }

  // Discard pending changes
  const handleDiscardChanges = () => {
    setPendingChanges(new Map())
    toast({
      title: "Changes Discarded",
      description: "All pending permission changes have been discarded",
    })
  }

  // Toggle category expansion
  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedCategories(newExpanded)
  }

  // Get risk level styling
  const getRiskBadge = (riskLevel: Permission['riskLevel']) => {
    const styles = {
      low: "bg-green-100 text-green-800",
      medium: "bg-yellow-100 text-yellow-800",
      high: "bg-red-100 text-red-800",
    }
    const icons = {
      low: <Shield className="h-3 w-3" />,
      medium: <Info className="h-3 w-3" />,
      high: <AlertTriangle className="h-3 w-3" />,
    }
    
    return (
      <Badge className={`${styles[riskLevel]} gap-1`} variant="secondary">
        {icons[riskLevel]}
        {riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)}
      </Badge>
    )
  }

  if (rolesError || permissionsError) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Error loading permissions: {rolesError?.message || permissionsError?.message || "Unknown error"}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <h3 className="text-lg font-medium">Permission Matrix</h3>
        <p className="text-muted-foreground">
          Manage role-based permissions and access control
        </p>
      </div>

      {/* Filters and Actions */}
      <Card>
        <CardHeader>
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
            <div className="flex flex-col sm:flex-row gap-4 flex-1">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Search permissions..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-full sm:w-64"
                />
              </div>

              {/* Filters */}
              <div className="flex gap-2">
                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {categories.map((category) => (
                      <SelectItem key={category} value={category}>
                        {category.charAt(0).toUpperCase() + category.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={riskFilter} onValueChange={setRiskFilter}>
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder="Risk" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Risk</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Actions */}
            {pendingChanges.size > 0 && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDiscardChanges}
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Discard ({pendingChanges.size})
                </Button>
                <Button
                  size="sm"
                  onClick={handleSaveChanges}
                  disabled={updateRole.isPending}
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes ({pendingChanges.size})
                </Button>
              </div>
            )}
          </div>

          {pendingChanges.size > 0 && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                You have {pendingChanges.size} pending permission change{pendingChanges.size > 1 ? 's' : ''}. 
                Don't forget to save your changes.
              </AlertDescription>
            </Alert>
          )}
        </CardHeader>
      </Card>

      {/* Permission Matrix */}
      <Card>
        <CardHeader>
          <CardTitle>Roles & Permissions</CardTitle>
          <CardDescription>
            {roles.length} roles, {Object.values(permissionsByCategory).flat().length} permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {rolesLoading || permissionsLoading ? (
            <div className="flex justify-center items-center h-32">
              <div className="text-muted-foreground">Loading permissions...</div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Roles Header */}
              <div className="sticky top-0 bg-background z-10 pb-2">
                <div className="grid gap-4" style={{ gridTemplateColumns: "300px repeat(auto-fit, minmax(120px, 1fr))" }}>
                  <div></div>
                  {roles.map((role) => (
                    <div key={role.id} className="text-center">
                      <div className="font-medium text-sm truncate">{role.name}</div>
                      <div className="text-xs text-muted-foreground truncate">{role.description}</div>
                      {role.isSystem && (
                        <Badge variant="secondary" className="mt-1 text-xs">System</Badge>
                      )}
                    </div>
                  ))}
                </div>
                <Separator className="mt-2" />
              </div>

              {/* Permission Categories */}
              {Object.entries(filteredCategories).map(([category, permissions]) => (
                <div key={category} className="space-y-2">
                  <Collapsible
                    open={expandedCategories.has(category)}
                    onOpenChange={() => toggleCategory(category)}
                  >
                    <CollapsibleTrigger asChild>
                      <Button
                        variant="ghost"
                        className="w-full justify-start p-2 h-auto"
                      >
                        <div className="flex items-center gap-2">
                          <Filter className="h-4 w-4" />
                          <span className="font-medium">
                            {category.charAt(0).toUpperCase() + category.slice(1)}
                          </span>
                          <Badge variant="outline">{permissions.length}</Badge>
                        </div>
                      </Button>
                    </CollapsibleTrigger>

                    <CollapsibleContent className="space-y-1">
                      {permissions.map((permission) => (
                        <div
                          key={permission.id}
                          className="grid gap-4 py-2 px-4 rounded-lg hover:bg-muted/50"
                          style={{ gridTemplateColumns: "300px repeat(auto-fit, minmax(120px, 1fr))" }}
                        >
                          {/* Permission Info */}
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{permission.name}</span>
                              {getRiskBadge(permission.riskLevel)}
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {permission.description}
                            </p>
                          </div>

                          {/* Role Checkboxes */}
                          {roles.map((role) => (
                            <div key={role.id} className="flex justify-center">
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Checkbox
                                      checked={hasPermission(role.id, permission.id)}
                                      onCheckedChange={(checked) => 
                                        handlePermissionChange(role.id, permission.id, checked as boolean)
                                      }
                                      disabled={role.isSystem}
                                    />
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>
                                      {hasPermission(role.id, permission.id) ? "Remove" : "Grant"} 
                                      {" "}{permission.name} for {role.name}
                                      {role.isSystem && " (System role - cannot modify)"}
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                          ))}
                        </div>
                      ))}
                    </CollapsibleContent>
                  </Collapsible>
                </div>
              ))}

              {Object.keys(filteredCategories).length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No permissions found matching your criteria
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
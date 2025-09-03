"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rolesApi, permissionsApi } from '@/lib/api'

export interface Role {
  id: string
  name: string
  description: string
  permissions: string[]
  isSystem: boolean
  createdAt: string
  updatedAt: string
}

export interface Permission {
  id: string
  name: string
  description: string
  category: string
  riskLevel: 'low' | 'medium' | 'high'
  dependencies?: string[]
}

export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: rolesApi.list,
    staleTime: 10 * 60 * 1000, // 10 minutes - roles don't change often
  })
}

export function useRole(id: string) {
  return useQuery({
    queryKey: ['roles', id],
    queryFn: () => rolesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateRole() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: rolesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] })
    },
  })
}

export function useUpdateRole() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, data }: { 
      id: string; 
      data: {
        name?: string;
        description?: string;
        permissions?: string[];
      }
    }) => rolesApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['roles'] })
      queryClient.invalidateQueries({ queryKey: ['roles', variables.id] })
    },
  })
}

export function useDeleteRole() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: rolesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] })
    },
  })
}

export function usePermissions(category?: string) {
  return useQuery({
    queryKey: ['permissions', category],
    queryFn: () => category ? permissionsApi.getByCategory(category) : permissionsApi.list(),
    staleTime: 15 * 60 * 1000, // 15 minutes - permissions are fairly static
  })
}

export function usePermissionsByCategory() {
  return useQuery({
    queryKey: ['permissions', 'all'],
    queryFn: permissionsApi.list,
    staleTime: 15 * 60 * 1000,
    select: (permissions: Permission[]) => {
      // Group permissions by category for easier display
      const grouped = permissions.reduce((acc, permission) => {
        if (!acc[permission.category]) {
          acc[permission.category] = []
        }
        acc[permission.category].push(permission)
        return acc
      }, {} as Record<string, Permission[]>)
      
      return grouped
    },
  })
}
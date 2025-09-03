"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi } from '@/lib/api'

export interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  role: string
  status: 'active' | 'inactive' | 'pending' | 'suspended'
  lastLogin?: string
  createdAt: string
  updatedAt: string
  permissions?: string[]
}

export interface UserFilters {
  status?: string
  role?: string
  skip?: number
  limit?: number
}

export function useUsers(filters?: UserFilters) {
  return useQuery({
    queryKey: ['users', filters],
    queryFn: () => usersApi.list(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useUser(id: string) {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => usersApi.get(id),
    enabled: !!id,
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, data }: { 
      id: string; 
      data: {
        firstName?: string;
        lastName?: string;
        role?: string;
        status?: 'active' | 'inactive' | 'pending' | 'suspended';
      }
    }) => usersApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      queryClient.invalidateQueries({ queryKey: ['users', variables.id] })
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: usersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useBulkUpdateUserStatus() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ userIds, status }: {
      userIds: string[];
      status: 'active' | 'inactive' | 'suspended';
    }) => usersApi.bulkUpdateStatus(userIds, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useInviteUser() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: usersApi.invite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
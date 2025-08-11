import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { locationsApi } from '@/lib/api';

export interface Location {
  id: string;
  org_id: string;
  name: string;
  type: string;
  address?: string;
  created_at: string;
  updated_at: string;
}

export function useLocations() {
  return useQuery<Location[], Error>({
    queryKey: ['locations'],
    queryFn: () => locationsApi.list().then(res => res.data),
  });
}

export function useLocation(id: string) {
  return useQuery<Location, Error>({
    queryKey: ['locations', id],
    queryFn: () => locationsApi.get(id).then(res => res.data),
    enabled: !!id,
  });
}

export function useCreateLocation() {
  const queryClient = useQueryClient();
  
  return useMutation<Location, Error, Partial<Location>>({
    mutationFn: (data) => locationsApi.create(data).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
    },
  });
}

export function useUpdateLocation() {
  const queryClient = useQueryClient();
  
  return useMutation<Location, Error, { id: string; data: Partial<Location> }>({
    mutationFn: ({ id, data }) => locationsApi.update(id, data).then(res => res.data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
      queryClient.invalidateQueries({ queryKey: ['locations', id] });
    },
  });
}

export function useDeleteLocation() {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: (id) => locationsApi.delete(id).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locations'] });
    },
  });
}
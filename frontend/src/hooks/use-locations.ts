import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { locationsApi } from '@/lib/api';
import { Location } from '@/types';

export function useLocations() {
  const query = useQuery({
    queryKey: ['locations'],
    queryFn: () => locationsApi.list().then(res => res.data),
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error: any) => {
      // Don't retry on 401/403 (auth issues)
      if (error?.response?.status === 401 || error?.response?.status === 403) {
        return false;
      }
      // Retry up to 2 times for other errors
      return failureCount < 2;
    },
  });

  return {
    locations: query.data,
    loading: query.isLoading,
    error: query.error?.message,
    refetch: query.refetch,
  };
}

export function useLocation(id: string) {
  const query = useQuery({
    queryKey: ['locations', id],
    queryFn: () => locationsApi.get(id).then(res => res.data),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error: any) => {
      // Don't retry on 401/403/404 (auth or not found issues)
      if (error?.response?.status === 401 || error?.response?.status === 403 || error?.response?.status === 404) {
        return false;
      }
      // Retry up to 2 times for other errors
      return failureCount < 2;
    },
  });

  return {
    location: query.data,
    loading: query.isLoading,
    error: query.error,
  };
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
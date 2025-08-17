import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi } from '@/lib/api';

export interface Product {
  id: string;
  org_id: string;
  sku: string;
  name: string;
  category?: string;
  cost?: number;
  price?: number;
  reorder_point?: number;
  created_at: string;
  updated_at: string;
}

export function useProducts() {
  const query = useQuery<Product[], Error>({
    queryKey: ['products'],
    queryFn: () => productsApi.list().then(res => res.data),
  });

  return {
    products: query.data || [],
    loading: query.isLoading,
    error: query.error?.message,
    refetch: query.refetch,
  };
}

export function useProduct(id: string) {
  const query = useQuery<Product, Error>({
    queryKey: ['products', id],
    queryFn: () => productsApi.get(id).then(res => res.data),
    enabled: !!id,
  });

  return {
    product: query.data,
    loading: query.isLoading,
    error: query.error?.message,
    refetch: query.refetch,
  };
}

export function useCreateProduct() {
  const queryClient = useQueryClient();
  
  return useMutation<Product, Error, Partial<Product>>({
    mutationFn: (data) => productsApi.create(data).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();
  
  return useMutation<Product, Error, { id: string; data: Partial<Product> }>({
    mutationFn: ({ id, data }) => productsApi.update(id, data).then(res => res.data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['products', id] });
    },
  });
}

export function useDeleteProduct() {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: (id) => productsApi.delete(id).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useBulkUpsertProducts() {
  const queryClient = useQueryClient();
  
  return useMutation<Product[], Error, Product[]>({
    mutationFn: (products) => productsApi.bulkUpsert(products).then(res => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}
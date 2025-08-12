import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { purchasingApi } from '@/lib/api';
import { PurchaseOrder, PurchaseOrderSummary } from '@/types';

export function usePurchaseOrders(filters?: {
  status?: string;
  supplier_id?: string;
  skip?: number;
  limit?: number;
}) {
  const query = useQuery<PurchaseOrderSummary[], Error>({
    queryKey: ['purchase-orders', filters],
    queryFn: () => purchasingApi.getPurchaseOrders(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  return {
    purchaseOrders: query.data,
    loading: query.isLoading,
    error: query.error?.message,
    refetch: query.refetch,
  };
}

export function usePurchaseOrder(id: string) {
  return useQuery<PurchaseOrder, Error>({
    queryKey: ['purchase-orders', id],
    queryFn: () => purchasingApi.getPurchaseOrder(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useCreatePurchaseOrder() {
  const queryClient = useQueryClient();
  
  return useMutation<PurchaseOrder, Error, any>({
    mutationFn: purchasingApi.createPurchaseOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
}

export function useUpdatePurchaseOrderStatus() {
  const queryClient = useQueryClient();
  
  return useMutation<PurchaseOrder, Error, { id: string; data: any }>({
    mutationFn: ({ id, data }) => purchasingApi.updatePurchaseOrderStatus(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      queryClient.invalidateQueries({ queryKey: ['purchase-orders', id] });
    },
  });
}

export function useDeletePurchaseOrder() {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: purchasingApi.deletePurchaseOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
}
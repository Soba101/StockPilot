import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '@/lib/api';

export interface StockSummary {
  product_id: string;
  product_name: string;
  product_sku: string;
  location_id: string;
  location_name: string;
  on_hand_quantity: number;
  allocated_quantity: number;
  available_quantity: number;
  reorder_point?: number;
  is_low_stock: boolean;
  is_out_of_stock: boolean;
  last_movement_date?: string;
}

export interface LocationStockSummary {
  location_id: string;
  location_name: string;
  total_products: number;
  low_stock_count: number;
  out_of_stock_count: number;
  total_stock_value: number;
  products: StockSummary[];
}

export interface InventorySummary {
  total_products: number;
  total_locations: number;
  low_stock_count: number;
  out_of_stock_count: number;
  total_stock_value: number;
  locations: LocationStockSummary[];
}

export interface InventoryMovement {
  id: string;
  product_id: string;
  location_id: string;
  quantity: number;
  movement_type: 'in' | 'out' | 'adjust' | 'transfer';
  reference?: string;
  notes?: string;
  timestamp: string;
  created_by?: string;
  created_at: string;
  product_name?: string;
  product_sku?: string;
  location_name?: string;
}

export interface StockAdjustment {
  product_id: string;
  location_id: string;
  new_quantity: number;
  reason: string;
  notes?: string;
}

export interface StockTransfer {
  product_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  reference?: string;
  notes?: string;
}

export function useInventory(locationId?: string) {
  return useQuery<InventorySummary, Error>({
    queryKey: ['inventory-summary', locationId],
    queryFn: () => inventoryApi.getSummary(locationId),
  });
}

export function useInventoryMovements(filters?: {
  productId?: string;
  locationId?: string;
  movementType?: string;
  startDate?: string;
  endDate?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery<InventoryMovement[], Error>({
    queryKey: ['inventory-movements', filters],
    queryFn: () => inventoryApi.getMovements(filters),
  });
}

export function useCreateMovement() {
  const queryClient = useQueryClient();
  
  return useMutation<InventoryMovement, Error, Omit<InventoryMovement, 'id' | 'created_at' | 'created_by'>>({
    mutationFn: inventoryApi.createMovement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-summary'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-movements'] });
    },
  });
}

export function useAdjustStock() {
  const queryClient = useQueryClient();
  
  return useMutation<InventoryMovement[], Error, { adjustments: StockAdjustment[] }>({
    mutationFn: inventoryApi.adjustStock,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-summary'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-movements'] });
    },
  });
}

export function useTransferStock() {
  const queryClient = useQueryClient();
  
  return useMutation<InventoryMovement[], Error, StockTransfer>({
    mutationFn: inventoryApi.transferStock,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-summary'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-movements'] });
    },
  });
}
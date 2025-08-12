import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';

export interface StockoutRiskRow {
  product_id: string;
  product_name: string;
  sku: string;
  on_hand: number;
  reorder_point?: number | null;
  velocity_7d?: number | null;
  velocity_30d?: number | null;
  velocity_56d?: number | null;
  velocity_source?: '7d' | '30d' | '56d' | 'none';
  forecast_30d_units?: number | null;
  days_to_stockout?: number | null;
  risk_level: 'none' | 'low' | 'medium' | 'high';
}

export function useStockoutRisk(days: number = 30) {
  const query = useQuery<StockoutRiskRow[]>({
    queryKey: ['stockout-risk', days],
    queryFn: () => analyticsApi.getStockoutRisk(days),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  return {
    data: query.data,
    loading: query.isLoading,
    error: query.error?.message,
    refetch: query.refetch,
  };
}

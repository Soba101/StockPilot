import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';

export interface SalesMetrics {
  total_revenue: number;
  total_units: number;
  avg_order_value: number;
  total_orders: number;
  revenue_growth: number;
  units_growth: number;
}

export interface TopProduct {
  name: string;
  sku: string;
  units: number;
  revenue: number;
  margin: number;
}

export interface CategoryData {
  category: string;
  revenue: number;
  percentage: number;
  growth: number;
}

export interface RecentSale {
  date: string;
  product: string;
  quantity: number;
  revenue: number;
  channel: string;
}

export interface RevenuePoint {
  date: string;
  revenue: number;
}

export interface AnalyticsData {
  sales_metrics: SalesMetrics;
  top_products: TopProduct[];
  category_data: CategoryData[];
  recent_sales: RecentSale[];
  revenue_trend: RevenuePoint[];
}

export function useAnalytics(days: number = 30) {
  const query = useQuery<AnalyticsData>({
    queryKey: ['analytics', days],
    queryFn: () => analyticsApi.getAnalytics(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });

  return {
    data: query.data,
    loading: query.isLoading,
    error: query.error?.message,
    refetch: query.refetch,
  };
}
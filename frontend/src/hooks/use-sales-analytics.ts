import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';

export interface ChannelPerformanceRow {
  channel: string;
  total_revenue: number;
  total_units: number;
  orders_count: number;
  avg_order_value: number;
  margin_percent: number;
}

export interface SalesDailyRow {
  sales_date: string;
  channel: string;
  location_name: string;
  product_name: string;
  sku: string;
  category: string;
  units_sold: number;
  gross_revenue: number;
  gross_margin: number;
  margin_percent: number;
  orders_count: number;
  units_7day_avg: number;
  units_30day_avg: number;
}

export interface SalesAnalyticsResponse {
  period_summary: any;
  daily_sales: SalesDailyRow[];
  channel_performance: ChannelPerformanceRow[];
  top_performing_products: any[];
  trending_analysis: {
    growth_products: { product_name: string; sku: string; trend_ratio: number }[];
    declining_products: { product_name: string; sku: string; trend_ratio: number }[];
  };
}

export function useSalesAnalytics(days: number = 30) {
  return useQuery<SalesAnalyticsResponse>({
    queryKey: ['sales-analytics', days],
    queryFn: () => analyticsApi.getSalesAnalytics(days),
    staleTime: 5 * 60 * 1000,
  });
}

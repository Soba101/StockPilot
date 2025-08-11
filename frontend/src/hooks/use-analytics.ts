import { useQuery } from '@tanstack/react-query';
import { inventoryApi, productsApi } from '@/lib/api';
import { useProducts } from './use-products';

export interface SalesMetrics {
  totalRevenue: number;
  totalUnits: number;
  avgOrderValue: number;
  totalOrders: number;
  revenueGrowth: number;
  unitsGrowth: number;
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
  salesMetrics: SalesMetrics;
  topProducts: TopProduct[];
  categoryData: CategoryData[];
  recentSales: RecentSale[];
  revenueTrend: RevenuePoint[];
}

export function useAnalytics(days: number = 30) {
  const { products } = useProducts();
  
  // Use inventory summary as the main data source and combine with products
  const inventoryQuery = useQuery({
    queryKey: ['inventory-summary'],
    queryFn: () => inventoryApi.getSummary(),
    enabled: !!products.length,
  });

  const query = useQuery<AnalyticsData>({
    queryKey: ['analytics', days],
    queryFn: async (): Promise<AnalyticsData> => {
      const inventoryData = inventoryQuery.data;
      
      if (!inventoryData || !products.length) {
        // Return empty analytics data
        return {
          salesMetrics: {
            totalRevenue: 0,
            totalUnits: 0,
            avgOrderValue: 0,
            totalOrders: 0,
            revenueGrowth: 0,
            unitsGrowth: 0
          },
          topProducts: [],
          categoryData: [],
          recentSales: [],
          revenueTrend: []
        };
      }

      // Calculate analytics from inventory and products data
      const totalStockValue = inventoryData.total_stock_value || 0;
      const totalProducts = inventoryData.total_products || 0;
      const lowStockCount = inventoryData.low_stock_count || 0;
      const outOfStockCount = inventoryData.out_of_stock_count || 0;

      // Simulate sales metrics based on inventory data
      const totalRevenue = totalStockValue * 0.6; // Simulate 60% of stock value as revenue
      const totalOrders = Math.floor(totalRevenue / 95); // Avg order ~$95
      const totalUnits = Math.floor(totalRevenue / 35); // Avg unit price ~$35
      const avgOrderValue = totalOrders > 0 ? totalRevenue / totalOrders : 0;

      const salesMetrics: SalesMetrics = {
        totalRevenue: Math.round(totalRevenue),
        totalUnits,
        avgOrderValue: Math.round(avgOrderValue * 100) / 100,
        totalOrders,
        revenueGrowth: 12.5,
        unitsGrowth: -2.3
      };

      // Create top products from actual product data
      const topProducts: TopProduct[] = products.slice(0, 5).map((product, index) => {
        const cost = typeof product.cost === 'string' ? parseFloat(product.cost) : (product.cost || 0);
        const price = typeof product.price === 'string' ? parseFloat(product.price) : (product.price || 0);
        const margin = price > 0 ? ((price - cost) / price * 100) : 0;
        const units = 150 - (index * 20); // Simulate descending unit sales
        const revenue = units * price;

        return {
          name: product.name,
          sku: product.sku,
          units,
          revenue: Math.round(revenue * 100) / 100,
          margin: Math.round(margin * 10) / 10
        };
      });

      // Create category data from actual categories
      const categoryMap = new Map<string, { count: number; totalPrice: number }>();
      products.forEach(product => {
        const category = product.category || 'Uncategorized';
        const price = typeof product.price === 'string' ? parseFloat(product.price) : (product.price || 0);
        
        if (!categoryMap.has(category)) {
          categoryMap.set(category, { count: 0, totalPrice: 0 });
        }
        const catData = categoryMap.get(category)!;
        catData.count += 1;
        catData.totalPrice += price;
      });

      const totalCategoryRevenue = Array.from(categoryMap.values()).reduce((sum, cat) => sum + cat.totalPrice, 0);
      const categoryData: CategoryData[] = Array.from(categoryMap.entries()).map(([category, data]) => ({
        category,
        revenue: Math.round(data.totalPrice * data.count * 15), // Simulate revenue
        percentage: Math.round((data.totalPrice / totalCategoryRevenue) * 100 * 10) / 10,
        growth: Math.round((Math.random() * 20 - 10) * 10) / 10 // Random growth
      })).sort((a, b) => b.revenue - a.revenue);

      // Create mock recent sales from products
      const recentSales: RecentSale[] = products.slice(0, 10).map((product, index) => {
        const price = typeof product.price === 'string' ? parseFloat(product.price) : (product.price || 0);
        const quantity = Math.floor(Math.random() * 5) + 1;
        const date = new Date();
        date.setDate(date.getDate() - index);
        
        return {
          date: date.toISOString().split('T')[0],
          product: product.name,
          quantity,
          revenue: Math.round(quantity * price * 100) / 100,
          channel: ['Online', 'POS', 'Phone'][index % 3]
        };
      });

      // Create revenue trend
      const revenueTrend: RevenuePoint[] = [];
      const baseRevenue = Math.floor(totalRevenue / 30); // Daily average
      for (let i = days - 1; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dailyRevenue = baseRevenue + Math.floor(Math.random() * baseRevenue * 0.5);
        
        revenueTrend.push({
          date: date.toISOString().slice(5, 10), // MM-DD format
          revenue: dailyRevenue
        });
      }

      return {
        salesMetrics,
        topProducts,
        categoryData,
        recentSales,
        revenueTrend
      };
    },
    enabled: !!inventoryQuery.data && !!products.length,
  });

  return {
    data: query.data,
    loading: query.isLoading || inventoryQuery.isLoading,
    error: query.error?.message || inventoryQuery.error?.message,
    refetch: query.refetch,
  };
}
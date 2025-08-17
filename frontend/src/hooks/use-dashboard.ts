import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { useProducts } from './use-products';
import { useInventory, useInventoryMovements } from './use-inventory';
import { useSalesAnalytics } from './use-sales-analytics';

export interface ActivityItem {
  action: string;
  product: string;
  timestamp: string;
  type: 'stock_in' | 'stock_out' | 'adjustment' | 'low_stock_alert';
}

export interface CategoryData {
  name: string;
  value: number;
  color: string;
}

export interface TrendData {
  current: number;
  previous: number;
  direction: 'up' | 'down' | 'neutral';
  percentage: number;
}

export interface DashboardStats {
  totalProducts: number;
  totalValue: number;
  lowStockCount: number;
  outOfStockCount: number;
  recentActivity: ActivityItem[];
  topCategories: CategoryData[];
  trends: {
    revenue: TrendData;
    units: TrendData;
    orders: TrendData;
  };
}

export function useDashboard(timePeriod: number = 30) {
  const { products, loading: productsLoading, error: productsError, refetch: refetchProducts } = useProducts();
  const { summary: inventorySummary, loading: inventoryLoading, error: inventoryError, refetch: refetchInventory } = useInventory();
  const { data: recentMovements, isLoading: movementsLoading } = useInventoryMovements({ limit: 5 });
  const { data: currentSalesData, isLoading: currentSalesLoading } = useSalesAnalytics(timePeriod);
  const { data: previousSalesData, isLoading: previousSalesLoading } = useSalesAnalytics(timePeriod * 2);
  
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const calculateTrends = () => {
    if (!currentSalesData?.daily_sales || !previousSalesData?.daily_sales) {
      return {
        revenue: { current: 0, previous: 0, direction: 'neutral' as const, percentage: 0 },
        units: { current: 0, previous: 0, direction: 'neutral' as const, percentage: 0 },
        orders: { current: 0, previous: 0, direction: 'neutral' as const, percentage: 0 },
      };
    }

    // Get current period data (most recent timePeriod days)
    const currentPeriodData = currentSalesData.daily_sales;
    
    // Get previous period data (timePeriod days before current period)
    const allPreviousData = previousSalesData.daily_sales;
    const currentDates = new Set(currentPeriodData.map(d => d.sales_date));
    const previousPeriodData = allPreviousData.filter(d => !currentDates.has(d.sales_date));

    const currentTotals = currentPeriodData.reduce(
      (acc, sale) => ({
        revenue: acc.revenue + sale.gross_revenue,
        units: acc.units + sale.units_sold,
        orders: acc.orders + sale.orders_count,
      }),
      { revenue: 0, units: 0, orders: 0 }
    );

    const previousTotals = previousPeriodData.reduce(
      (acc, sale) => ({
        revenue: acc.revenue + sale.gross_revenue,
        units: acc.units + sale.units_sold,
        orders: acc.orders + sale.orders_count,
      }),
      { revenue: 0, units: 0, orders: 0 }
    );

    const calculateTrend = (current: number, previous: number): { direction: 'up' | 'down' | 'neutral'; percentage: number } => {
      if (previous === 0) {
        return { 
          direction: current > 0 ? 'up' : 'neutral', 
          percentage: current > 0 ? 100 : 0 
        };
      }
      const percentage = ((current - previous) / previous) * 100;
      return {
        direction: percentage > 0 ? 'up' : percentage < 0 ? 'down' : 'neutral',
        percentage: Math.abs(percentage)
      };
    };

    const revenueTrend = calculateTrend(currentTotals.revenue, previousTotals.revenue);
    const unitsTrend = calculateTrend(currentTotals.units, previousTotals.units);
    const ordersTrend = calculateTrend(currentTotals.orders, previousTotals.orders);

    return {
      revenue: {
        current: currentTotals.revenue,
        previous: previousTotals.revenue,
        direction: revenueTrend.direction,
        percentage: revenueTrend.percentage,
      },
      units: {
        current: currentTotals.units,
        previous: previousTotals.units,
        direction: unitsTrend.direction,
        percentage: unitsTrend.percentage,
      },
      orders: {
        current: currentTotals.orders,
        previous: previousTotals.orders,
        direction: ordersTrend.direction,
        percentage: ordersTrend.percentage,
      },
    };
  };

  const calculateStats = () => {
    const trends = calculateTrends();

    // Use real inventory data if available, fallback to products-only data
    if (inventorySummary) {
      // Use real inventory summary data
      const totalProducts = inventorySummary.total_products;
      const totalValue = inventorySummary.total_stock_value;
      const lowStockCount = inventorySummary.low_stock_count;
      const outOfStockCount = inventorySummary.out_of_stock_count;

      // Calculate category distribution from products
      const categoryMap = new Map<string, number>();
      products?.forEach(product => {
        const category = product.category || 'Uncategorized';
        categoryMap.set(category, (categoryMap.get(category) || 0) + 1);
      });

      const colors = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];
      const topCategories = Array.from(categoryMap.entries())
        .map(([name, value], index) => ({ 
          name, 
          value, 
          color: colors[index % colors.length] 
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 5);

      // Use real recent movements data
      const recentActivity: ActivityItem[] = recentMovements?.slice(0, 3).map(movement => {
        const getActionText = (type: string) => {
          switch (type) {
            case 'in': return 'Stock Added';
            case 'out': return 'Stock Removed';
            case 'adjust': return 'Stock Adjusted';
            case 'transfer': return 'Stock Transferred';
            default: return 'Inventory Movement';
          }
        };

        const getTimeAgo = (timestamp: string) => {
          const now = new Date();
          const moveTime = new Date(timestamp);
          const diffHours = Math.floor((now.getTime() - moveTime.getTime()) / (1000 * 60 * 60));
          if (diffHours < 1) return 'Just now';
          if (diffHours === 1) return '1 hour ago';
          if (diffHours < 24) return `${diffHours} hours ago`;
          return `${Math.floor(diffHours / 24)} days ago`;
        };

        return {
          action: getActionText(movement.movement_type),
          product: movement.product_name || 'Unknown Product',
          timestamp: getTimeAgo(movement.timestamp),
          type: movement.movement_type as ActivityItem['type']
        };
      }) || [];

      setStats({
        totalProducts,
        totalValue,
        lowStockCount,
        outOfStockCount,
        recentActivity,
        topCategories,
        trends
      });
    } else if (products?.length) {
      // Fallback to products-only data when inventory summary isn't available
      setStats({
        totalProducts: products.length,
        totalValue: 0, // Can't calculate without stock data
        lowStockCount: 0,
        outOfStockCount: 0,
        recentActivity: [],
        topCategories: [],
        trends
      });
    } else {
      // No data available
      setStats({
        totalProducts: 0,
        totalValue: 0,
        lowStockCount: 0,
        outOfStockCount: 0,
        recentActivity: [],
        topCategories: [],
        trends
      });
    }
  };

  useEffect(() => {
    const isLoading = productsLoading || inventoryLoading || movementsLoading || currentSalesLoading || previousSalesLoading;
    const hasError = productsError || inventoryError;

    if (!isLoading && !hasError) {
      calculateStats();
      setLoading(false);
      setError(null);
    } else if (hasError) {
      setError(typeof hasError === 'string' ? hasError : hasError?.message || 'Unknown error');
      setLoading(false);
    } else {
      setLoading(isLoading);
    }
  }, [products, productsLoading, productsError, inventorySummary, inventoryLoading, inventoryError, recentMovements, movementsLoading, currentSalesData, currentSalesLoading, previousSalesData, previousSalesLoading, timePeriod]);

  const refetch = async () => {
    setLoading(true);
    try {
      await Promise.all([
        refetchProducts(),
        refetchInventory()
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh dashboard');
    }
  };

  return {
    stats,
    loading: loading || productsLoading || inventoryLoading,
    error: error || productsError || inventoryError,
    refetch
  };
}
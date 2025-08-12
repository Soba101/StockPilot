import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { useProducts } from './use-products';
import { useInventory, useInventoryMovements } from './use-inventory';

interface DashboardStats {
  totalProducts: number;
  totalValue: number;
  lowStockCount: number;
  outOfStockCount: number;
  recentActivity: ActivityItem[];
  topCategories: CategoryData[];
}

interface ActivityItem {
  action: string;
  product: string;
  timestamp: string;
  type: 'stock_in' | 'stock_out' | 'adjustment' | 'low_stock_alert';
}

interface CategoryData {
  name: string;
  value: number;
  color: string;
}

export function useDashboard() {
  const { products, loading: productsLoading, error: productsError, refetch: refetchProducts } = useProducts();
  const { summary: inventorySummary, loading: inventoryLoading, error: inventoryError, refetch: refetchInventory } = useInventory();
  const { data: recentMovements, loading: movementsLoading } = useInventoryMovements({ limit: 5 });
  const { user, isAuthenticated } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const calculateStats = () => {
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
        topCategories
      });
    } else if (products?.length) {
      // Fallback to products-only data when inventory summary isn't available
      setStats({
        totalProducts: products.length,
        totalValue: 0, // Can't calculate without stock data
        lowStockCount: 0,
        outOfStockCount: 0,
        recentActivity: [],
        topCategories: []
      });
    } else {
      // No data available
      setStats({
        totalProducts: 0,
        totalValue: 0,
        lowStockCount: 0,
        outOfStockCount: 0,
        recentActivity: [],
        topCategories: []
      });
    }
  };

  useEffect(() => {
    const isLoading = productsLoading || inventoryLoading || movementsLoading;
    const hasError = productsError || inventoryError;

    if (!isLoading && !hasError) {
      calculateStats();
      setLoading(false);
      setError(null);
    } else if (hasError) {
      setError(hasError);
      setLoading(false);
    } else {
      setLoading(isLoading);
    }
  }, [products, productsLoading, productsError, inventorySummary, inventoryLoading, inventoryError, recentMovements, movementsLoading]);

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
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { useProducts } from './use-products';

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
  const { user, isAuthenticated } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const calculateStats = () => {
    if (!products?.length) {
      setStats({
        totalProducts: 0,
        totalValue: 0,
        lowStockCount: 0,
        outOfStockCount: 0,
        recentActivity: [],
        topCategories: []
      });
      return;
    }

    const totalProducts = products.length;
    
    // Simulate current stock levels for demonstration
    const productsWithStock = products.map(product => ({
      ...product,
      currentStock: Math.floor(Math.random() * 100) + 1
    }));

    const lowStockItems = productsWithStock.filter(p => p.currentStock <= p.reorder_point && p.currentStock > 0);
    const outOfStockItems = productsWithStock.filter(p => p.currentStock === 0);

    const totalValue = productsWithStock.reduce((sum, product) => {
      const price = typeof product.price === 'string' ? parseFloat(product.price) : (product.price || 0);
      return sum + (price * product.currentStock);
    }, 0);

    // Calculate category distribution
    const categoryMap = new Map<string, number>();
    products.forEach(product => {
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

    // Generate recent activity (simulated)
    const recentActivity: ActivityItem[] = [
      {
        action: 'Stock Added',
        product: products[Math.floor(Math.random() * products.length)]?.name || 'Unknown Product',
        timestamp: '2 hours ago',
        type: 'stock_in'
      },
      {
        action: 'Low Stock Alert',
        product: products[Math.floor(Math.random() * products.length)]?.name || 'Unknown Product',
        timestamp: '4 hours ago',
        type: 'low_stock_alert'
      },
      {
        action: 'Product Updated',
        product: products[Math.floor(Math.random() * products.length)]?.name || 'Unknown Product',
        timestamp: '6 hours ago',
        type: 'adjustment'
      }
    ];

    setStats({
      totalProducts,
      totalValue,
      lowStockCount: lowStockItems.length,
      outOfStockCount: outOfStockItems.length,
      recentActivity,
      topCategories
    });
  };

  useEffect(() => {
    if (!productsLoading && !productsError) {
      calculateStats();
      setLoading(false);
      setError(null);
    } else if (productsError) {
      setError(productsError);
      setLoading(false);
    }
  }, [products, productsLoading, productsError]);

  const refetch = async () => {
    setLoading(true);
    try {
      await refetchProducts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh dashboard');
    }
  };

  return {
    stats,
    loading: loading || productsLoading,
    error: error || productsError,
    refetch
  };
}
import axios from 'axios';
import type { Product, Organization, Location, InventoryMovement, PurchaseOrder } from '@/types';

// Dynamically determine API base URL so the app works when accessed via LAN IP.
// Priority:
// 1. NEXT_PUBLIC_API_BASE env var (explicit override, full URL)
// 2. In browser on dev port 3000: use relative '/api' so Next.js rewrite proxies to backend (no CORS, works over LAN)
// 3. Otherwise: construct direct host:8000/api/v1 URL (e.g., when served from production / different port)
const resolvedApiBase = (() => {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_BASE) {
    return process.env.NEXT_PUBLIC_API_BASE.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    if (window.location.port === '3000') {
      return '/api'; // leverage Next.js dev rewrite: /api/:path* -> http://localhost:8000/api/v1/:path*
    }
    const protocol = window.location.protocol;
    const host = window.location.hostname; // preserves LAN IP when accessed via 192.168.x.x
    return `${protocol}//${host}:8000/api/v1`;
  }
  return 'http://127.0.0.1:8000/api/v1';
})();

// Create axios instance with base configuration
const api = axios.create({
  baseURL: resolvedApiBase,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

  // Use same base to avoid cross-origin issues (works with relative /api in dev)
  const refreshUrl = `${resolvedApiBase.replace(/\/$/, '')}/auth/refresh`;
  const response = await axios.post(refreshUrl, { refresh_token: refreshToken });

        const { access_token } = response.data;
        localStorage.setItem('access_token', access_token);
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// API endpoints
export const productsApi = {
  list: () => api.get('/products/'),
  get: (id: string) => api.get(`/products/${id}`),
  create: (data: Omit<Product, 'id' | 'created_at' | 'updated_at'>) => api.post('/products/', data),
  update: (id: string, data: Partial<Omit<Product, 'id' | 'created_at' | 'updated_at'>>) => api.put(`/products/${id}`, data),
  delete: (id: string) => api.delete(`/products/${id}`),
  bulkUpsert: (products: Omit<Product, 'id' | 'created_at' | 'updated_at'>[]) => api.post('/products/bulk_upsert', { products }),
  getBySku: (sku: string) => api.get(`/products/sku/${sku}`),
  getByOrg: (orgId: string) => api.get(`/products/organization/${orgId}`),
};

export const organizationsApi = {
  list: () => api.get('/organizations/'),
  get: (id: string) => api.get(`/organizations/${id}`),
  create: (data: Omit<Organization, 'id' | 'created_at' | 'updated_at'>) => api.post('/organizations/', data),
  update: (id: string, data: Partial<Omit<Organization, 'id' | 'created_at' | 'updated_at'>>) => api.put(`/organizations/${id}`, data),
  delete: (id: string) => api.delete(`/organizations/${id}`),
};

export const locationsApi = {
  list: () => api.get('/locations/'),
  get: (id: string) => api.get(`/locations/${id}`),
  create: (data: Omit<Location, 'id' | 'created_at' | 'updated_at'>) => api.post('/locations/', data),
  update: (id: string, data: Partial<Omit<Location, 'id' | 'created_at' | 'updated_at'>>) => api.put(`/locations/${id}`, data),
  delete: (id: string) => api.delete(`/locations/${id}`),
  getByOrg: (orgId: string) => api.get(`/locations/organization/${orgId}`),
};

export const authApi = {
  login: (email: string, password: string) => 
    api.post('/auth/login', { email, password }),
  refresh: (refreshToken: string) => 
    api.post('/auth/refresh', { refresh_token: refreshToken }),
};

export const inventoryApi = {
  getSummary: (locationId?: string) => {
    const params = locationId ? { location_id: locationId } : {};
    return api.get('/inventory/summary', { params }).then(res => res.data);
  },
  getMovements: (filters?: {
    productId?: string;
    locationId?: string;
    movementType?: string;
    startDate?: string;
    endDate?: string;
    skip?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.productId) params.append('product_id', filters.productId);
    if (filters?.locationId) params.append('location_id', filters.locationId);
    if (filters?.movementType) params.append('movement_type', filters.movementType);
    if (filters?.startDate) params.append('start_date', filters.startDate);
    if (filters?.endDate) params.append('end_date', filters.endDate);
    if (filters?.skip) params.append('skip', filters.skip.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());
    
    return api.get(`/inventory/movements?${params.toString()}`).then(res => res.data);
  },
  getMovement: (id: string) => 
    api.get(`/inventory/movements/${id}`).then(res => res.data),
  createMovement: (data: Omit<InventoryMovement, 'id' | 'created_at'>) => 
    api.post('/inventory/movements', data).then(res => res.data),
  adjustStock: (data: { adjustments: { product_id: string; location_id: string; quantity: number; notes?: string }[] }) => 
    api.post('/inventory/adjust', data).then(res => res.data),
  transferStock: (data: { product_id: string; from_location_id: string; to_location_id: string; quantity: number; notes?: string }) => 
    api.post('/inventory/transfer', data).then(res => res.data),
};

// Chat API
export const chatApi = {
  query: (payload: { prompt: string; intent?: string; params?: Record<string, any> }) =>
    api.post('/chat2/query', { message: payload.prompt, intent: payload.intent, options: payload.params })
      .then(res => res.data)
      .then(data => {
        // Transform hybrid chat response to traditional chat format for compatibility
        if (data.route) {
          return {
            intent: data.route === 'BI' ? 'analytics' : null,
            title: getTitleFromRoute(data.route),
            answer_summary: data.answer,
            data: data.cards?.[0]?.data ? {
              columns: Object.keys(data.cards[0].data[0] || {}).map(name => ({ name, type: 'string' })),
              rows: data.cards[0].data
            } : { columns: [], rows: [] },
            query_explainer: {
              definition: `${data.route} route with ${data.confidence} confidence`,
              sql: null,
              sources: []
            },
            freshness: {
              generated_at: new Date().toISOString(),
              data_fresh_at: data.provenance?.data?.refreshed_at || null,
              max_lag_seconds: null
            },
            confidence: {
              level: data.confidence > 0.75 ? 'high' : data.confidence > 0.55 ? 'medium' : 'low',
              reasons: [data.reason || 'hybrid_routing']
            },
            source: 'hybrid',
            warnings: []
          };
        }
        return data; // Fallback for non-hybrid responses
      }),
};

// Helper function to get title from route
function getTitleFromRoute(route: string): string {
  const titles = {
    'BI': 'Business Intelligence Analysis',
    'RAG': 'Document Search Results', 
    'MIXED': 'Combined Analysis & Documentation',
    'OPEN': 'StockPilot Assistant',
    'NO_ANSWER': 'Unable to Process Query'
  };
  return titles[route as keyof typeof titles] || 'StockPilot Response';
}

export const analyticsApi = {
  getAnalytics: (days: number = 30) => 
    api.get(`/analytics?days=${days}`).then(res => res.data),
  getSalesAnalytics: (days: number = 30) =>
    api.get(`/analytics/sales?days=${days}`).then(res => res.data),
  getInventoryAnalytics: () => 
    api.get('/inventory-analytics').then(res => res.data),
  getStockoutRisk: (days: number = 30) => 
    api.get(`/analytics/stockout-risk?days=${days}`).then(res => res.data),
};

export const purchasingApi = {
  getPurchaseOrders: (filters?: {
    status?: string;
    supplier_id?: string;
    skip?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.supplier_id) params.append('supplier_id', filters.supplier_id);
    if (filters?.skip) params.append('skip', filters.skip.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());
    
    return api.get(`/purchasing/purchase-orders?${params.toString()}`).then(res => res.data);
  },
  getPurchaseOrder: (id: string) => 
    api.get(`/purchasing/purchase-orders/${id}`).then(res => res.data),
  createPurchaseOrder: (data: Omit<PurchaseOrder, 'id' | 'created_at' | 'updated_at'>) => 
    api.post('/purchasing/purchase-orders', data).then(res => res.data),
  updatePurchaseOrderStatus: (id: string, data: { status: PurchaseOrder['status'] }) => 
    api.put(`/purchasing/purchase-orders/${id}/status`, data).then(res => res.data),
  deletePurchaseOrder: (id: string) => 
    api.delete(`/purchasing/purchase-orders/${id}`).then(res => res.data),
  
  // Reorder suggestions endpoints
  getReorderSuggestions: (filters?: {
    location_id?: string;
    strategy?: 'latest' | 'conservative';
    horizon_days_override?: number;
    include_zero_velocity?: boolean;
    min_days_cover?: number;
    max_days_cover?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.location_id) params.append('location_id', filters.location_id);
    if (filters?.strategy) params.append('strategy', filters.strategy);
    if (filters?.horizon_days_override) params.append('horizon_days_override', filters.horizon_days_override.toString());
    if (filters?.include_zero_velocity !== undefined) params.append('include_zero_velocity', filters.include_zero_velocity.toString());
    if (filters?.min_days_cover) params.append('min_days_cover', filters.min_days_cover.toString());
    if (filters?.max_days_cover) params.append('max_days_cover', filters.max_days_cover.toString());
    
    return api.get(`/purchasing/reorder-suggestions?${params.toString()}`).then(res => res.data);
  },
  explainReorderSuggestion: (productId: string, filters?: {
    strategy?: 'latest' | 'conservative';
    horizon_days_override?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.strategy) params.append('strategy', filters.strategy);
    if (filters?.horizon_days_override) params.append('horizon_days_override', filters.horizon_days_override.toString());
    
    return api.get(`/purchasing/reorder-suggestions/explain/${productId}?${params.toString()}`).then(res => res.data);
  },
  createDraftPurchaseOrders: (data: {
    product_ids: string[];
    strategy?: 'latest' | 'conservative';
    horizon_days_override?: number;
    auto_number?: boolean;
  }) => 
    api.post('/purchasing/reorder-suggestions/draft-po', data).then(res => res.data),
};

export default api;
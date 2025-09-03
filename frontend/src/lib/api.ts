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
    api
      .post('/chat2/query', { message: payload.prompt, options: payload.params })
      .then(res => res.data)
      .then((data: any) => {
        // Transform unified backend schema to UI-friendly shape expected by chat page
        const route: string = data?.route || 'OPEN';
        const answer: string = data?.answer || '';
  const confidenceNum: number = typeof data?.confidence === 'number' ? data.confidence : 0;
  const confidenceLevel = (confidenceNum >= 0.6 ? 'high' : confidenceNum >= 0.3 ? 'medium' : 'low') as 'high' | 'medium' | 'low';
  const source = (route === 'RAG' || route === 'BI' ? 'rules' : 'llm') as 'rules' | 'llm';
        const followUps: string[] = Array.isArray(data?.follow_ups) ? data.follow_ups : [];

  return {
    title: getTitleFromRoute(route),
          answer_summary: answer,
          data: undefined, // No tabular data in chat for now
          confidence: { level: confidenceLevel },
          source,
          query_explainer: {},
          follow_ups: followUps,
        };
      }),
};

// Helper function to get title from route
function getTitleFromRoute(route: string): string {
  // Unify assistant persona across all routes
  return 'StockPilot Assistant';
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

export const usersApi = {
  list: (filters?: {
    status?: string;
    role?: string;
    skip?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.role) params.append('role', filters.role);
    if (filters?.skip) params.append('skip', filters.skip.toString());
    if (filters?.limit) params.append('limit', filters.limit.toString());
    
    return api.get(`/settings/users?${params.toString()}`).then(res => res.data);
  },
  get: (id: string) => api.get(`/settings/users/${id}`).then(res => res.data),
  create: (data: {
    email: string;
    firstName: string;
    lastName: string;
    role: string;
    status?: 'active' | 'inactive' | 'pending' | 'suspended';
  }) => api.post('/settings/users', data).then(res => res.data),
  update: (id: string, data: {
    firstName?: string;
    lastName?: string;
    role?: string;
    status?: 'active' | 'inactive' | 'pending' | 'suspended';
  }) => api.put(`/settings/users/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/settings/users/${id}`).then(res => res.data),
  bulkUpdateStatus: (userIds: string[], status: 'active' | 'inactive' | 'suspended') => 
    api.post('/settings/users/bulk-status', { user_ids: userIds, status }).then(res => res.data),
  invite: (data: {
    email: string;
    firstName: string;
    lastName: string;
    role: string;
  }) => api.post('/settings/users/invite', data).then(res => res.data),
};

export const rolesApi = {
  list: () => api.get('/settings/roles').then(res => res.data),
  get: (id: string) => api.get(`/settings/roles/${id}`).then(res => res.data),
  create: (data: {
    name: string;
    description: string;
    permissions: string[];
  }) => api.post('/settings/roles', data).then(res => res.data),
  update: (id: string, data: {
    name?: string;
    description?: string;
    permissions?: string[];
  }) => api.put(`/settings/roles/${id}`, data).then(res => res.data),
  delete: (id: string) => api.delete(`/settings/roles/${id}`).then(res => res.data),
};

export const permissionsApi = {
  list: () => api.get('/settings/permissions').then(res => res.data),
  getByCategory: (category?: string) => {
    const params = category ? `?category=${category}` : '';
    return api.get(`/settings/permissions${params}`).then(res => res.data);
  },
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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { purchasingApi } from '@/lib/api';

// Types for reorder suggestions
export interface ReorderSuggestion {
  product_id: string;
  sku: string;
  name: string;
  supplier_id?: string;
  supplier_name?: string;
  on_hand: number;
  incoming: number;
  days_cover_current?: number;
  days_cover_after?: number;
  recommended_quantity: number;
  chosen_velocity?: number;
  velocity_source: string;
  horizon_days: number;
  demand_forecast_units: number;
  reasons: string[];
  adjustments: string[];
}

export interface ReorderSuggestionsResponse {
  suggestions: ReorderSuggestion[];
  summary: {
    total_suggestions: number;
    total_recommended_quantity: number;
    suppliers_involved: number;
    reason_breakdown: Record<string, number>;
    strategy_used: string;
    filters_applied: Record<string, any>;
  };
  generated_at: string;
  parameters: ReorderSuggestionsRequest;
}

export interface ReorderSuggestionsRequest {
  location_id?: string;
  strategy?: 'latest' | 'conservative';
  horizon_days_override?: number;
  include_zero_velocity?: boolean;
  min_days_cover?: number;
  max_days_cover?: number;
}

export interface ReorderExplanation {
  product_id: string;
  sku: string;
  name: string;
  skipped?: boolean;
  skip_reason?: string;
  recommendation?: {
    quantity: number;
    supplier_id?: string;
    supplier_name?: string;
  };
  explanation?: {
    inputs: Record<string, any>;
    calculations: Record<string, any>;
    logic_path: string[];
  };
  reasons: string[];
  adjustments: string[];
  coverage?: {
    days_cover_current?: number;
    days_cover_after?: number;
  };
  velocity?: {
    chosen_velocity?: number;
    source: string;
  };
}

export interface DraftPO {
  supplier_id: string;
  supplier_name: string;
  po_number: string;
  items: DraftPOItem[];
  total_items: number;
  total_quantity: number;
  estimated_total?: number;
  lead_time_days: number;
  minimum_order_quantity: number;
  payment_terms?: string;
  created_at: string;
  expected_delivery?: string;
}

export interface DraftPOItem {
  product_id: string;
  sku: string;
  product_name: string;
  quantity: number;
  unit_cost?: number;
  line_total?: number;
  on_hand: number;
  recommended_quantity: number;
  reasons: string[];
  adjustments: string[];
}

export interface DraftPOResponse {
  draft_pos: DraftPO[];
  summary: {
    total_draft_pos: number;
    total_items: number;
    total_quantity: number;
    total_estimated_value?: number;
    suppliers: string[];
  };
  created_at: string;
}

// Hook for getting reorder suggestions
export function useReorderSuggestions(filters?: ReorderSuggestionsRequest) {
  const query = useQuery<ReorderSuggestionsResponse, Error>({
    queryKey: ['reorder-suggestions', filters],
    queryFn: () => purchasingApi.getReorderSuggestions(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false, // Prevent excessive re-fetching
  });

  return {
    suggestions: query.data?.suggestions || [],
    summary: query.data?.summary,
    parameters: query.data?.parameters,
    generatedAt: query.data?.generated_at,
    loading: query.isLoading,
    error: query.error?.message,
    refetch: query.refetch,
  };
}

// Hook for explaining a single reorder suggestion
export function useReorderExplanation(
  productId: string,
  filters?: {
    strategy?: 'latest' | 'conservative';
    horizon_days_override?: number;
  }
) {
  return useQuery<ReorderExplanation, Error>({
    queryKey: ['reorder-explanation', productId, filters],
    queryFn: () => purchasingApi.explainReorderSuggestion(productId, filters),
    enabled: !!productId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for creating draft purchase orders
export function useCreateDraftPOs() {
  const queryClient = useQueryClient();
  
  return useMutation<
    DraftPOResponse,
    Error,
    {
      product_ids: string[];
      strategy?: 'latest' | 'conservative';
      horizon_days_override?: number;
      auto_number?: boolean;
    }
  >({
    mutationFn: purchasingApi.createDraftPurchaseOrders,
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      queryClient.invalidateQueries({ queryKey: ['reorder-suggestions'] });
    },
  });
}

// Custom hook for managing reorder suggestions filters
export function useReorderFilters() {
  const defaultFilters: ReorderSuggestionsRequest = {
    strategy: 'latest',
    include_zero_velocity: false,
  };

  return {
    defaultFilters,
    strategyOptions: [
      { value: 'latest', label: 'Latest Velocity (7d → 30d → 56d)' },
      { value: 'conservative', label: 'Conservative (minimum non-zero)' },
    ],
    reasonLabels: {
      'BELOW_REORDER_POINT': 'Below Reorder Point',
      'LEAD_TIME_RISK': 'Lead Time Risk',
      'MOQ_ENFORCED': 'MOQ Enforced',
      'PACK_ROUNDED': 'Pack Size Rounded',
      'CAPPED_BY_MAX_DAYS': 'Capped by Max Stock Days',
      'ZERO_VELOCITY_SKIPPED': 'Zero Velocity (Skipped)',
      'INCOMING_COVERAGE': 'Has Incoming Stock',
      'NO_VELOCITY': 'No Velocity Data',
    },
    velocitySourceLabels: {
      '7d': '7-day average',
      '30d': '30-day average',
      '56d': '56-day average',
      'none': 'No velocity data',
      'mixed': 'Mixed sources',
    },
  };
}
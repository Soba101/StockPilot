export interface Organization {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export interface Location {
  id: string
  org_id: string
  name: string
  type: 'warehouse' | 'store' | 'virtual'
  address?: string
  created_at: string
  updated_at: string
}

export interface Product {
  id: string
  org_id: string
  sku: string
  name: string
  description?: string
  category?: string
  cost?: number | string
  price?: number | string
  uom: string
  reorder_point: number
  created_at: string
  updated_at: string
}

export interface InventoryMovement {
  id: string
  product_id: string
  location_id: string
  quantity: number
  movement_type: 'in' | 'out' | 'adjust' | 'transfer'
  reference?: string
  notes?: string
  timestamp: string
  created_by?: string
  created_at: string
}

export interface StockSummary {
  product_id: string
  product_name: string
  product_sku: string
  location_id: string
  location_name: string
  on_hand_quantity: number
  available_quantity: number
  reorder_point?: number
  is_low_stock: boolean
  is_out_of_stock: boolean
  last_movement_date?: string
}

export interface LocationStockSummary {
  location_id: string
  location_name: string
  total_products: number
  low_stock_count: number
  out_of_stock_count: number
  total_stock_value: number
  products: StockSummary[]
}

export interface InventorySummaryResponse {
  total_products: number
  total_locations: number
  low_stock_count: number
  out_of_stock_count: number
  total_stock_value: number
  locations: LocationStockSummary[]
}

export interface Supplier {
  id: string
  org_id: string
  name: string
  contact_person?: string
  email?: string
  phone?: string
  address?: string
  lead_time_days: number
  minimum_order_quantity: number
  payment_terms?: string
  is_active: string
  created_at: string
  updated_at: string
}

export interface PurchaseOrderItem {
  id: string
  purchase_order_id: string
  product_id: string
  quantity: number
  unit_cost: number
  total_cost: number
  received_quantity: number
  created_at: string
  updated_at: string
  product_name?: string
  product_sku?: string
}

export interface PurchaseOrder {
  id: string
  org_id: string
  supplier_id: string
  po_number: string
  status: 'draft' | 'pending' | 'ordered' | 'received' | 'cancelled'
  order_date?: string
  expected_date?: string
  received_date?: string
  total_amount: number
  notes?: string
  created_at: string
  updated_at: string
  created_by?: string
  supplier_name?: string
  items: PurchaseOrderItem[]
}

export interface PurchaseOrderSummary {
  id: string
  po_number: string
  supplier_name: string
  status: 'draft' | 'pending' | 'ordered' | 'received' | 'cancelled'
  total_amount: number
  order_date?: string
  expected_date?: string
  item_count: number
}
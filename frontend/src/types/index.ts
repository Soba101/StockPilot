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
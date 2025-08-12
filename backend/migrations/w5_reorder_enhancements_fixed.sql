-- W5 Implementation Migration: Reorder Enhancements (Fixed Version)
-- Adds new product fields and performance indices for reorder suggestions

-- First, add the new product fields for reorder suggestions
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS safety_stock_days INTEGER DEFAULT 3,
ADD COLUMN IF NOT EXISTS preferred_supplier_id UUID REFERENCES suppliers(id),
ADD COLUMN IF NOT EXISTS pack_size INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS max_stock_days INTEGER;

-- Update existing products to have default values where null
UPDATE products SET safety_stock_days = 3 WHERE safety_stock_days IS NULL;
UPDATE products SET pack_size = 1 WHERE pack_size IS NULL;

-- Add performance indices for reorder suggestions workload
-- These indices optimize the reorder_inputs mart query and API performance

-- Index for inventory movements aggregation (on_hand calculation)
-- This speeds up the sum(movements) GROUP BY product_id, org_id query
CREATE INDEX IF NOT EXISTS idx_inventory_movements_product_type ON inventory_movements(product_id, movement_type);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_org_product ON inventory_movements(product_id) INCLUDE (quantity, movement_type);

-- Index for purchase order items aggregation (incoming stock calculation)
-- This speeds up the sum(poi.quantity) GROUP BY product_id query for pending POs
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_product ON purchase_order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_product_qty ON purchase_order_items(product_id) INCLUDE (quantity);

-- Index for purchase orders filtering by status and expected date
-- This speeds up filtering for pending/ordered POs within horizon dates
CREATE INDEX IF NOT EXISTS idx_purchase_orders_status_expected ON purchase_orders(status, expected_date) WHERE status IN ('pending', 'ordered', 'confirmed');
CREATE INDEX IF NOT EXISTS idx_purchase_orders_org_status ON purchase_orders(org_id, status);

-- Composite index for supplier lookups in reorder mart
CREATE INDEX IF NOT EXISTS idx_suppliers_org_active ON suppliers(org_id, is_active) WHERE is_active = 'true';

-- Index for product-supplier relationships
CREATE INDEX IF NOT EXISTS idx_products_preferred_supplier ON products(preferred_supplier_id) WHERE preferred_supplier_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_org_supplier ON products(org_id, preferred_supplier_id);

-- Additional indices for dbt mart performance
-- These optimize the joins in the reorder_inputs mart

-- Compound index for products by org with reorder fields
CREATE INDEX IF NOT EXISTS idx_products_reorder_fields ON products(org_id) INCLUDE (
    sku, name, category, cost, price, reorder_point, safety_stock_days, 
    pack_size, max_stock_days, preferred_supplier_id
);

-- Index for movement timestamp filtering (for recent movement queries)
CREATE INDEX IF NOT EXISTS idx_inventory_movements_timestamp_product ON inventory_movements(timestamp DESC, product_id);

-- Index for order items with timestamp for sales velocity calculations
CREATE INDEX IF NOT EXISTS idx_order_items_product_date ON order_items(product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_date_status ON orders(ordered_at, status) WHERE status IN ('fulfilled', 'completed', 'shipped');

-- Add some constraints to ensure data quality for reorder calculations
ALTER TABLE products 
ADD CONSTRAINT IF NOT EXISTS chk_products_safety_stock_days CHECK (safety_stock_days >= 0),
ADD CONSTRAINT IF NOT EXISTS chk_products_pack_size CHECK (pack_size >= 1),
ADD CONSTRAINT IF NOT EXISTS chk_products_max_stock_days CHECK (max_stock_days IS NULL OR max_stock_days > 0),
ADD CONSTRAINT IF NOT EXISTS chk_products_reorder_point CHECK (reorder_point >= 0);

ALTER TABLE suppliers
ADD CONSTRAINT IF NOT EXISTS chk_suppliers_lead_time CHECK (lead_time_days >= 0),
ADD CONSTRAINT IF NOT EXISTS chk_suppliers_moq CHECK (minimum_order_quantity >= 1);

-- Update existing supplier records to ensure data quality
UPDATE suppliers SET lead_time_days = 7 WHERE lead_time_days IS NULL OR lead_time_days < 0;
UPDATE suppliers SET minimum_order_quantity = 1 WHERE minimum_order_quantity IS NULL OR minimum_order_quantity < 1;

-- Update supplier table to match the model (add missing fields if not exist)
ALTER TABLE suppliers 
ADD COLUMN IF NOT EXISTS contact_person VARCHAR(255),
ADD COLUMN IF NOT EXISTS email VARCHAR(255),
ADD COLUMN IF NOT EXISTS phone VARCHAR(50),
ADD COLUMN IF NOT EXISTS address TEXT,
ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(100),
ADD COLUMN IF NOT EXISTS is_active VARCHAR(10) DEFAULT 'true';

-- Update existing suppliers to have proper is_active value
UPDATE suppliers SET is_active = 'true' WHERE is_active IS NULL;

-- Add constraint for is_active field
ALTER TABLE suppliers 
ADD CONSTRAINT IF NOT EXISTS chk_suppliers_is_active CHECK (is_active IN ('true', 'false'));

-- Statistics update to help query planner with new indices
ANALYZE products;
ANALYZE suppliers; 
ANALYZE inventory_movements;
ANALYZE purchase_orders;
ANALYZE purchase_order_items;

-- Create a view for quick reorder insights (optional, for monitoring)
CREATE OR REPLACE VIEW v_reorder_health AS
SELECT 
    org_id,
    COUNT(*) as total_products,
    COUNT(*) FILTER (WHERE preferred_supplier_id IS NOT NULL) as products_with_preferred_supplier,
    COUNT(*) FILTER (WHERE safety_stock_days > 0) as products_with_safety_stock,
    COUNT(*) FILTER (WHERE pack_size > 1) as products_with_pack_constraints,
    COUNT(*) FILTER (WHERE max_stock_days IS NOT NULL) as products_with_max_stock_limits,
    AVG(reorder_point) as avg_reorder_point,
    AVG(safety_stock_days) as avg_safety_stock_days
FROM products 
GROUP BY org_id;

COMMENT ON VIEW v_reorder_health IS 'Health check view for reorder suggestion data quality and coverage';

-- Add comments for documentation
COMMENT ON COLUMN products.safety_stock_days IS 'Buffer stock in days to handle demand variability';
COMMENT ON COLUMN products.preferred_supplier_id IS 'Default supplier for reorder suggestions';
COMMENT ON COLUMN products.pack_size IS 'Minimum order pack/case size (quantities rounded up to multiples)';
COMMENT ON COLUMN products.max_stock_days IS 'Maximum stock coverage in days (caps reorder quantities)';

COMMENT ON INDEX idx_inventory_movements_product_type IS 'Optimizes on_hand calculations for reorder suggestions';
COMMENT ON INDEX idx_purchase_order_items_product IS 'Optimizes incoming stock calculations for reorder suggestions';
COMMENT ON INDEX idx_purchase_orders_status_expected IS 'Optimizes filtering pending POs by expected delivery date';
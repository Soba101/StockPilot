-- Staging model for products
-- Clean and standardize product data from the raw products table

select
    id as product_id,
    org_id,
    sku,
    name as product_name,
    description,
    category,
    cost,
    price,
    uom as unit_of_measure,
    reorder_point,
    -- W5 reorder enhancement fields
    safety_stock_days,
    preferred_supplier_id,
    pack_size,
    max_stock_days,
    created_at,
    updated_at
from {{ source('stockpilot', 'products') }}
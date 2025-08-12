-- Staging model for inventory movements
-- Clean and standardize inventory movement data

select
    im.id as movement_id,
    im.product_id,
    p.org_id,  -- Get org_id from products table
    im.location_id,
    im.quantity,
    im.movement_type,
    im.reference,
    im.notes,
    im.timestamp as movement_timestamp,
    im.created_by,
    im.created_at
from {{ source('stockpilot', 'inventory_movements') }} im
join {{ source('stockpilot', 'products') }} p on im.product_id = p.id
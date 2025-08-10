-- Staging model for inventory movements
-- Clean and standardize inventory movement data

select
    id as movement_id,
    product_id,
    location_id,
    quantity,
    movement_type,
    reference,
    notes,
    timestamp as movement_timestamp,
    created_by,
    created_at
from {{ source('stockpilot', 'inventory_movements') }}
-- Daily inventory snapshot mart
-- Calculates on-hand quantity for each product-location combination by date

{{ config(materialized='table') }}

with daily_movements as (
    select
        product_id,
        location_id,
        date_trunc('day', movement_timestamp) as snapshot_date,
        sum(case 
            when movement_type in ('in', 'adjust') then quantity
            when movement_type in ('out', 'transfer') then -quantity
            else 0
        end) as daily_change
    from {{ ref('stg_inventory_movements') }}
    group by 1, 2, 3
),

cumulative_inventory as (
    select
        product_id,
        location_id,
        snapshot_date,
        daily_change,
        sum(daily_change) over (
            partition by product_id, location_id 
            order by snapshot_date 
            rows unbounded preceding
        ) as on_hand_quantity
    from daily_movements
)

select
    product_id,
    location_id,
    snapshot_date,
    on_hand_quantity,
    -- Calculate allocated quantity (placeholder for future order allocation logic)
    0 as allocated_quantity,
    -- Available = on_hand - allocated
    greatest(on_hand_quantity - 0, 0) as available_quantity,
    current_timestamp as created_at
from cumulative_inventory
where on_hand_quantity > 0  -- Only include locations with stock
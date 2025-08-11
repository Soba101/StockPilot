-- Daily inventory snapshot mart
-- Calculates on-hand, allocated, and available quantities for each product-location combination by date

{{ config(
    materialized='table',
    indexes=[
        {'columns': ['product_id', 'location_id', 'snapshot_date'], 'unique': true},
        {'columns': ['snapshot_date']},
        {'columns': ['product_id']},
        {'columns': ['location_id']}
    ]
) }}

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
),

-- Get product details for reorder point comparisons
products as (
    select 
        product_id,
        reorder_point,
        cost
    from {{ ref('stg_products') }}
),

-- Calculate allocated quantities from pending orders (future enhancement)
-- For now, we'll use a placeholder calculation
allocated_quantities as (
    select
        product_id,
        location_id,
        snapshot_date,
        -- Placeholder: could calculate from order_items where order status = 'pending'
        0 as allocated_quantity
    from cumulative_inventory
)

select
    ci.product_id,
    ci.location_id,
    ci.snapshot_date,
    ci.on_hand_quantity,
    coalesce(aq.allocated_quantity, 0) as allocated_quantity,
    -- Available = on_hand - allocated (never negative)
    greatest(ci.on_hand_quantity - coalesce(aq.allocated_quantity, 0), 0) as available_quantity,
    -- Add reorder point for easy comparison
    p.reorder_point,
    -- Stock status calculations
    case 
        when ci.on_hand_quantity <= 0 then 'out_of_stock'
        when p.reorder_point is not null and ci.on_hand_quantity <= p.reorder_point then 'low_stock'
        else 'in_stock'
    end as stock_status,
    -- Stock value calculation
    coalesce(ci.on_hand_quantity * p.cost, 0) as stock_value,
    -- Days of stock remaining (placeholder - will enhance with velocity data in W4)
    case 
        when ci.on_hand_quantity > 0 then 999999  -- placeholder for infinite days
        else 0
    end as days_of_stock,
    current_timestamp as created_at
from cumulative_inventory ci
left join products p on ci.product_id = p.product_id
left join allocated_quantities aq on ci.product_id = aq.product_id 
    and ci.location_id = aq.location_id 
    and ci.snapshot_date = aq.snapshot_date
-- Include all records, even zero stock for complete tracking
where ci.on_hand_quantity >= 0
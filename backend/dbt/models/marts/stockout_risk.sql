-- Stockout risk analysis
-- Identifies products at risk of stocking out based on current inventory and velocity

{{ config(materialized='table') }}

with latest_inventory as (
    select
        product_id,
        location_id,
        available_quantity as current_stock,
        row_number() over (
            partition by product_id, location_id 
            order by snapshot_date desc
        ) as rn
    from {{ ref('inventory_snapshot_daily') }}
),

latest_velocity as (
    select
        product_id,
        location_id,
        velocity_for_calculations as daily_velocity,
        row_number() over (
            partition by product_id, location_id 
            order by sale_date desc
        ) as rn
    from {{ ref('velocity_analysis') }}
),

stockout_analysis as (
    select
        i.product_id,
        i.location_id,
        i.current_stock,
        coalesce(v.daily_velocity, 0.1) as daily_velocity,
        -- Days until stockout = current_stock / daily_velocity
        case 
            when v.daily_velocity > 0 then i.current_stock / v.daily_velocity
            else 999  -- Effectively infinite if no velocity
        end as days_until_stockout
    from latest_inventory i
    left join latest_velocity v 
        on i.product_id = v.product_id 
        and i.location_id = v.location_id
        and v.rn = 1
    where i.rn = 1
)

select
    sa.product_id,
    sa.location_id,
    p.sku,
    p.product_name,
    l.location_name,
    sa.current_stock,
    round(sa.daily_velocity, 2) as daily_velocity,
    round(sa.days_until_stockout, 1) as days_until_stockout,
    case
        when sa.days_until_stockout <= 7 then 'CRITICAL'
        when sa.days_until_stockout <= 14 then 'WARNING'
        when sa.days_until_stockout <= 30 then 'WATCH'
        else 'OK'
    end as risk_level,
    p.reorder_point,
    case 
        when sa.current_stock <= p.reorder_point then true 
        else false 
    end as below_reorder_point,
    current_timestamp as created_at
from stockout_analysis sa
join {{ ref('stg_products') }} p on sa.product_id = p.product_id
join {{ ref('stg_locations') }} l on sa.location_id = l.location_id
where sa.current_stock > 0  -- Only include products with current stock
order by sa.days_until_stockout asc
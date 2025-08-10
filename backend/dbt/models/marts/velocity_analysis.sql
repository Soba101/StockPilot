-- Product velocity analysis
-- Calculates 8-week moving average daily sales velocity

{{ config(materialized='table') }}

with daily_outbound as (
    select
        product_id,
        location_id,
        date_trunc('day', movement_timestamp) as sale_date,
        sum(case when movement_type = 'out' then quantity else 0 end) as units_sold
    from {{ ref('stg_inventory_movements') }}
    where movement_type = 'out'
    group by 1, 2, 3
),

velocity_calculation as (
    select
        product_id,
        location_id,
        sale_date,
        units_sold,
        -- 8-week (56 days) moving average
        avg(units_sold) over (
            partition by product_id, location_id
            order by sale_date
            rows between 55 preceding and current row
        ) as daily_velocity_8wk_ma
    from daily_outbound
)

select
    product_id,
    location_id,
    sale_date,
    units_sold,
    daily_velocity_8wk_ma,
    case 
        when daily_velocity_8wk_ma > 0 then daily_velocity_8wk_ma
        else 0.1  -- Minimum epsilon to avoid division by zero
    end as velocity_for_calculations,
    current_timestamp as created_at
from velocity_calculation
where sale_date >= current_date - interval '90 days'  -- Keep 90 days of history
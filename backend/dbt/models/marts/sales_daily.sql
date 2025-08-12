{{ config(materialized='table') }}

-- Daily sales aggregation by product, location, and channel
-- Includes revenue, units sold, margin calculations

with daily_sales as (
    select
        -- Date dimensions
        date_trunc('day', o.ordered_at) as sales_date,
        extract(year from o.ordered_at) as year,
        extract(month from o.ordered_at) as month,
        extract(day from o.ordered_at) as day,
        extract(dow from o.ordered_at) as day_of_week,
        
        -- Business dimensions
        o.org_id,
        o.channel,
        o.location_id,
        l.location_name,
        oi.product_id,
        p.product_name,
        p.sku,
        p.category,
        
        -- Metrics
        sum(oi.quantity) as units_sold,
        sum(oi.line_total) as gross_revenue,
        sum(oi.discount) as total_discount,
        avg(oi.unit_price) as avg_unit_price,
        sum(oi.quantity * p.cost) as total_cost,
        sum(oi.line_total - (oi.quantity * coalesce(p.cost, 0))) as gross_margin,
        
        -- Derived metrics  
        case 
            when sum(oi.line_total) > 0 
            then (sum(oi.line_total - (oi.quantity * coalesce(p.cost, 0))) / sum(oi.line_total)) * 100 
            else 0 
        end as margin_percent,
        
        count(distinct o.order_id) as orders_count,
        
        -- Min/max for analysis
        min(oi.unit_price) as min_unit_price,
        max(oi.unit_price) as max_unit_price

    from {{ ref('stg_orders') }} o
    join {{ ref('stg_order_items') }} oi on o.order_id = oi.order_id
    join {{ ref('stg_products') }} p on oi.product_id = p.product_id
    join {{ ref('stg_locations') }} l on o.location_id = l.location_id
    
    where o.status in ('fulfilled', 'completed', 'shipped')  -- Only count completed sales
        and o.ordered_at is not null
    
    group by
        sales_date,
        extract(year from o.ordered_at),
        extract(month from o.ordered_at), 
        extract(day from o.ordered_at),
        extract(dow from o.ordered_at),
        o.org_id,
        o.channel,
        o.location_id,
        l.location_name,
        oi.product_id,
        p.product_name,
        p.sku,
        p.category
),

-- Add rolling calculations
sales_with_trends as (
    select
        *,
        -- 7-day rolling average
        avg(units_sold) over (
            partition by product_id, location_id 
            order by sales_date 
            rows between 6 preceding and current row
        ) as units_7day_avg,
        
        -- 30-day rolling average  
        avg(units_sold) over (
            partition by product_id, location_id 
            order by sales_date 
            rows between 29 preceding and current row
        ) as units_30day_avg,
        
        -- 56-day rolling average (longer-term velocity)
        avg(units_sold) over (
            partition by product_id, location_id 
            order by sales_date 
            rows between 55 preceding and current row
        ) as units_56day_avg,
        
        -- Previous day comparison
        lag(units_sold, 1) over (
            partition by product_id, location_id 
            order by sales_date
        ) as units_prev_day,
        
        -- Week over week comparison (same day previous week)
        lag(units_sold, 7) over (
            partition by product_id, location_id 
            order by sales_date
        ) as units_prev_week
        
    from daily_sales
),

final as (
    select
        *,
        -- Simple 30 day unit forecast using preferred available velocity hierarchy
        (coalesce(units_7day_avg, units_30day_avg, units_56day_avg) * 30)::numeric as forecast_30d_units
    from sales_with_trends
)

select * from final
order by sales_date desc, gross_revenue desc
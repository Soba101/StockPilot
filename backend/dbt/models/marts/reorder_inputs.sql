{{ config(materialized='table') }}

-- Reorder inputs mart combining product info, suppliers, velocity metrics, inventory on-hand, and inbound PO quantities
-- Used by purchase suggestions algorithm to compute reorder recommendations

with products_with_suppliers as (
    select
        p.org_id,
        p.product_id,
        p.sku,
        p.product_name,
        p.category,
        p.cost,
        p.price,
        p.reorder_point,
        p.safety_stock_days,
        p.pack_size,
        p.max_stock_days,
        p.preferred_supplier_id,
        
        -- Supplier info (preferred or fallback to any available)
        s.id as supplier_id,
        s.name as supplier_name,
        s.lead_time_days,
        s.minimum_order_quantity as moq,
        s.payment_terms,
        s.is_active as supplier_is_active
        
    from {{ ref('stg_products') }} p
    left join {{ source('stockpilot', 'suppliers') }} s 
        on p.preferred_supplier_id = s.id 
        and p.org_id = s.org_id
        and s.is_active = 'true'
),

-- Get current inventory on-hand from movements
inventory_on_hand as (
    select
        org_id,
        product_id,
        -- Sum all movements to get current on-hand
        sum(case 
            when movement_type in ('in', 'adjust') then quantity
            when movement_type in ('out', 'transfer') then -quantity
            else 0
        end) as on_hand
    from {{ ref('stg_inventory_movements') }}
    group by org_id, product_id
),

-- Get latest velocity metrics from sales_daily
latest_velocities as (
    select
        org_id,
        product_id,
        -- Get the most recent velocity data available
        units_7day_avg,
        units_30day_avg,
        units_56day_avg,
        forecast_30d_units,
        sales_date as last_sales_date,
        
        -- Prioritize velocity: latest non-null from 7d > 30d > 56d
        coalesce(units_7day_avg, units_30day_avg, units_56day_avg) as chosen_velocity_latest,
        
        -- Conservative velocity: minimum non-zero velocity
        case 
            when units_7day_avg > 0 and units_30day_avg > 0 and units_56day_avg > 0 
                then least(units_7day_avg, units_30day_avg, units_56day_avg)
            when units_7day_avg > 0 and units_30day_avg > 0 
                then least(units_7day_avg, units_30day_avg)
            when units_7day_avg > 0 and units_56day_avg > 0 
                then least(units_7day_avg, units_56day_avg)
            when units_30day_avg > 0 and units_56day_avg > 0 
                then least(units_30day_avg, units_56day_avg)
            when units_7day_avg > 0 then units_7day_avg
            when units_30day_avg > 0 then units_30day_avg
            when units_56day_avg > 0 then units_56day_avg
            else null
        end as chosen_velocity_conservative
        
    from (
        select 
            *,
            row_number() over (partition by org_id, product_id order by sales_date desc) as rn
        from {{ ref('sales_daily') }}
        where sales_date >= current_date - interval '90 days'  -- Only recent data
    ) ranked
    where rn = 1
),

-- Get inbound PO quantities (pending/ordered POs)
inbound_po_quantities as (
    select
        po.org_id,
        poi.product_id,
        sum(poi.quantity) as incoming_units_total,
        
        -- Quantities expected within different horizons
        sum(case 
            when po.expected_date <= current_date + interval '7 days' then poi.quantity 
            else 0 
        end) as incoming_units_7d,
        
        sum(case 
            when po.expected_date <= current_date + interval '14 days' then poi.quantity 
            else 0 
        end) as incoming_units_14d,
        
        sum(case 
            when po.expected_date <= current_date + interval '30 days' then poi.quantity 
            else 0 
        end) as incoming_units_30d,
        
        sum(case 
            when po.expected_date <= current_date + interval '60 days' then poi.quantity 
            else 0 
        end) as incoming_units_60d
        
    from {{ source('stockpilot', 'purchase_orders') }} po
    join {{ source('stockpilot', 'purchase_order_items') }} poi on po.id = poi.purchase_order_id
    where po.status in ('pending', 'ordered', 'confirmed')
        and po.expected_date is not null
    group by po.org_id, poi.product_id
),

final as (
    select
        -- Product & supplier identifiers
        pws.org_id,
        pws.product_id,
        pws.sku,
        pws.product_name,
        pws.category,
        
        -- Product economics
        pws.cost,
        pws.price,
        
        -- Reorder parameters
        pws.reorder_point,
        coalesce(pws.safety_stock_days, 3) as safety_stock_days,
        coalesce(pws.pack_size, 1) as pack_size,
        pws.max_stock_days,
        
        -- Supplier info
        pws.supplier_id,
        pws.supplier_name,
        coalesce(pws.lead_time_days, 7) as lead_time_days,
        coalesce(pws.moq, 1) as moq,
        pws.payment_terms,
        coalesce(pws.supplier_is_active, 'false') as supplier_is_active,
        
        -- Current inventory
        coalesce(ioh.on_hand, 0) as on_hand,
        
        -- Velocity metrics
        lv.units_7day_avg,
        lv.units_30day_avg,
        lv.units_56day_avg,
        lv.forecast_30d_units,
        lv.chosen_velocity_latest,
        lv.chosen_velocity_conservative,
        lv.last_sales_date,
        
        -- Velocity source indicators
        case 
            when lv.units_7day_avg is not null then '7d'
            when lv.units_30day_avg is not null then '30d'
            when lv.units_56day_avg is not null then '56d'
            else 'none'
        end as velocity_source_latest,
        
        case 
            when lv.chosen_velocity_conservative is not null then
                case 
                    when lv.chosen_velocity_conservative = lv.units_7day_avg then '7d'
                    when lv.chosen_velocity_conservative = lv.units_30day_avg then '30d'
                    when lv.chosen_velocity_conservative = lv.units_56day_avg then '56d'
                    else 'mixed'
                end
            else 'none'
        end as velocity_source_conservative,
        
        -- Inbound quantities
        coalesce(ipq.incoming_units_total, 0) as incoming_units_total,
        coalesce(ipq.incoming_units_7d, 0) as incoming_units_7d,
        coalesce(ipq.incoming_units_14d, 0) as incoming_units_14d,
        coalesce(ipq.incoming_units_30d, 0) as incoming_units_30d,
        coalesce(ipq.incoming_units_60d, 0) as incoming_units_60d,
        
        -- Computed horizon (lead time + safety stock, min 7)
        greatest(coalesce(pws.lead_time_days, 7) + coalesce(pws.safety_stock_days, 3), 7) as horizon_days,
        
        -- Data quality indicators
        case when pws.supplier_id is null then true else false end as missing_supplier,
        case when lv.chosen_velocity_latest is null then true else false end as no_velocity_data,
        case when ioh.on_hand < 0 then true else false end as negative_inventory,
        
        current_timestamp as computed_at
        
    from products_with_suppliers pws
    left join inventory_on_hand ioh 
        on pws.org_id = ioh.org_id 
        and pws.product_id = ioh.product_id
    left join latest_velocities lv 
        on pws.org_id = lv.org_id 
        and pws.product_id = lv.product_id
    left join inbound_po_quantities ipq 
        on pws.org_id = ipq.org_id 
        and pws.product_id = ipq.product_id
)

select * from final
order by org_id, product_name
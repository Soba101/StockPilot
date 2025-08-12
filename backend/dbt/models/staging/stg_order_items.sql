{{ config(materialized='view') }}

with order_items as (
    select 
        id as order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        discount,
        -- Calculate line totals
        (quantity * unit_price) as line_subtotal,
        ((quantity * unit_price) - coalesce(discount, 0)) as line_total,
        created_at
    from {{ source('stockpilot', 'order_items') }}
)

select * from order_items
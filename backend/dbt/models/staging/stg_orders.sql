{{ config(materialized='view') }}

with orders as (
    select 
        id as order_id,
        org_id,
        order_number,
        channel,
        status,
        ordered_at,
        fulfilled_at,
        location_id,
        total_amount,
        created_at,
        updated_at
    from {{ source('stockpilot', 'orders') }}
)

select * from orders
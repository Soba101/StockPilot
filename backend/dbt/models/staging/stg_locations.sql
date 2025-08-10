-- Staging model for locations
-- Clean and standardize location data

select
    id as location_id,
    org_id,
    name as location_name,
    type as location_type,
    address,
    created_at,
    updated_at
from {{ source('stockpilot', 'locations') }}
-- Create user if it doesn't exist (for external connections)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'stockpilot') THEN
        CREATE ROLE stockpilot WITH LOGIN PASSWORD 'stockpilot_dev' SUPERUSER CREATEDB CREATEROLE;
    END IF;
END $$;

-- Ensure database exists
SELECT 'CREATE DATABASE stockpilot OWNER stockpilot'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'stockpilot')\gexec

-- Connect to stockpilot database and run the rest of the initialization
\c stockpilot stockpilot;

-- Rest of initialization script (from original init.sql)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables... (continuing with original script)
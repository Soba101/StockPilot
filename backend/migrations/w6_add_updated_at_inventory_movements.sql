-- Migration: Add updated_at column to inventory_movements
-- Safe to run multiple times (IF NOT EXISTS pattern for Postgres 9.6+ not available for columns; use DO block)
DO $$
BEGIN
    -- Only add column if it does not exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='inventory_movements' AND column_name='updated_at'
    ) THEN
        ALTER TABLE inventory_movements ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

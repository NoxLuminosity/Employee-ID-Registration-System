-- SQL script to add suffix and location_branch columns to employees table
-- Run this in your Supabase SQL Editor or SQLite database

-- Add suffix column
ALTER TABLE employees ADD COLUMN IF NOT EXISTS suffix VARCHAR(20) DEFAULT '';

-- Add location_branch column
ALTER TABLE employees ADD COLUMN IF NOT EXISTS location_branch VARCHAR(100) DEFAULT '';

-- Verify columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'employees' 
  AND column_name IN ('suffix', 'location_branch');

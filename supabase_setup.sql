-- ============================================
-- Supabase Database Setup for Employee ID Registration
-- Run this script in Supabase SQL Editor
-- ============================================

-- Create employees table
CREATE TABLE IF NOT EXISTS employees (
    id BIGSERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    first_name TEXT,
    middle_initial TEXT,
    last_name TEXT,
    suffix TEXT,
    id_nickname TEXT,
    id_number TEXT NOT NULL,
    position TEXT NOT NULL,
    location_branch TEXT,
    department TEXT NOT NULL,
    email TEXT,
    personal_number TEXT,
    photo_path TEXT NOT NULL,
    photo_url TEXT,
    new_photo BOOLEAN DEFAULT TRUE,
    new_photo_url TEXT,
    nobg_photo_url TEXT,
    signature_path TEXT,
    signature_url TEXT,
    status TEXT DEFAULT 'Reviewing',
    date_last_modified TEXT,
    id_generated BOOLEAN DEFAULT FALSE,
    render_url TEXT,
    emergency_name TEXT,
    emergency_contact TEXT,
    emergency_address TEXT
);

-- ============================================
-- Schema migrations (safe for existing tables)
-- ============================================
-- The application inserts these columns when running on Vercel/Supabase.
-- If your table was created before these fields existed, inserts will fail with:
--   PGRST204: Could not find the '<column>' column of 'employees' in the schema cache

ALTER TABLE employees ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS middle_initial TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS last_name TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS suffix TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS location_branch TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS suffix TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS resolved_printer_branch TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS field_officer_type TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS field_clearance TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS fo_division TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS fo_department TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS fo_campaign TEXT;

-- Ensure status check constraint includes all valid statuses
-- If the constraint already exists, drop and recreate it
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'employees_status_check' AND table_name = 'employees'
  ) THEN
    ALTER TABLE employees DROP CONSTRAINT employees_status_check;
  END IF;
  ALTER TABLE employees ADD CONSTRAINT employees_status_check
    CHECK (status IN ('Reviewing', 'Rendered', 'Approved', 'Sent to POC', 'Completed', 'Removed'));
END $$;

-- Create index for faster status queries
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);

-- Create index for faster date ordering
CREATE INDEX IF NOT EXISTS idx_employees_date ON employees(date_last_modified DESC);

-- Enable Row Level Security (RLS) - Optional but recommended
-- Uncomment these lines if you want to use RLS
-- ALTER TABLE employees ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (for service key)
-- CREATE POLICY "Allow all operations" ON employees FOR ALL USING (true);

-- ============================================
-- OAuth State Storage (Required for Vercel Serverless)
-- ============================================
-- This table stores OAuth PKCE state for the Lark SSO flow.
-- In serverless environments, in-memory storage doesn't work
-- because each request may hit a different instance.

CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    code_verifier TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '10 minutes')
);

-- Index for cleanup of expired states
CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at);

-- Auto-cleanup function for expired OAuth states
CREATE OR REPLACE FUNCTION cleanup_expired_oauth_states()
RETURNS void AS $$
BEGIN
    DELETE FROM oauth_states WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Ask PostgREST (Supabase API layer) to reload its schema cache.
-- This helps the API see newly-added columns immediately.
-- If you don't have permissions for NOTIFY, you can remove this and wait a minute.
NOTIFY pgrst, 'reload schema';

-- ============================================
-- Verification: Run after creating table
-- ============================================
-- SELECT * FROM employees LIMIT 1;
-- SELECT * FROM oauth_states LIMIT 1;

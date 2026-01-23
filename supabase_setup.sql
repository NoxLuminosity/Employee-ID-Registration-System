-- ============================================
-- Supabase Database Setup for Employee ID Registration
-- Run this script in Supabase SQL Editor
-- ============================================

-- Create employees table
CREATE TABLE IF NOT EXISTS employees (
    id BIGSERIAL PRIMARY KEY,
    employee_name TEXT NOT NULL,
    id_nickname TEXT,
    id_number TEXT NOT NULL,
    position TEXT NOT NULL,
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

-- ============================================
-- Verification: Run after creating table
-- ============================================
-- SELECT * FROM employees LIMIT 1;
-- SELECT * FROM oauth_states LIMIT 1;

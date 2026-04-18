-- =====================================================
-- MIGRATION: Add Authentication Columns to Sellers Table
-- This ONLY adds new columns, does NOT modify existing ones
-- Run this in Supabase SQL Editor
-- =====================================================

-- Add password_hash column for custom authentication
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- Add seller_type column to distinguish between MERCHANT and FARMER
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS seller_type VARCHAR(50) DEFAULT 'MERCHANT';

-- Add farm-specific columns (for farmers)
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS farm_name VARCHAR(255);
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS farm_type VARCHAR(50);
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS state VARCHAR(100);

-- Add email verification status
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false;

-- Add last login tracking
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- Create index on email for faster login queries
CREATE INDEX IF NOT EXISTS idx_sellers_email ON sellers(email);

-- Create index on seller_type for filtering
CREATE INDEX IF NOT EXISTS idx_sellers_seller_type ON sellers(seller_type);

-- Create index on status
CREATE INDEX IF NOT EXISTS idx_sellers_status ON sellers(status);

-- =====================================================
-- ROW LEVEL SECURITY POLICIES
-- Required because sellers table uses custom auth (not Supabase Auth)
-- =====================================================

-- Ensure RLS is enabled on the sellers table
ALTER TABLE sellers ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Allow anonymous signup insert" ON sellers;
DROP POLICY IF EXISTS "Allow anonymous select for login" ON sellers;
DROP POLICY IF EXISTS "Allow anonymous update for profile" ON sellers;

-- Policy 1: Allow anonymous users to INSERT (create new accounts during signup)
-- This is needed because signup happens before authentication
CREATE POLICY "Allow anonymous signup insert" ON sellers
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Policy 2: Allow anonymous users to SELECT (needed for login verification)
-- Login checks if email exists and verifies password_hash
CREATE POLICY "Allow anonymous select for login" ON sellers
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Policy 3: Allow anonymous users to UPDATE (needed for profile updates)
-- Since we use custom auth (localStorage), Supabase sees all requests as anon
CREATE POLICY "Allow anonymous update for profile" ON sellers
    FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- RESULT
-- =====================================================
SELECT 'Migration completed! Changes made to sellers table:
COLUMNS ADDED:
- password_hash (for authentication)
- seller_type (MERCHANT or FARMER)
- farm_name (for farmers)
- farm_type (for farmers)
- state (location)
- email_verified
- last_login_at

RLS POLICIES ADDED:
- Allow anonymous signup insert (for creating accounts)
- Allow anonymous select for login (for verifying credentials)
- Allow anonymous update for profile (for updating seller profiles)' as result;

-- Enable the pg_cron extension first
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Create pending_orders table
CREATE TABLE IF NOT EXISTS pending_orders (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    items JSONB NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    shipping DECIMAL(10,2) NOT NULL DEFAULT 10.00,
    tax DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 hour'
);

-- Add RLS policies
ALTER TABLE pending_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own pending orders"
    ON pending_orders FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own pending orders"
    ON pending_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Create index for cleanup
CREATE INDEX pending_orders_expires_at_idx ON pending_orders(expires_at);

-- Create cleanup function that runs every hour
CREATE OR REPLACE FUNCTION cleanup_expired_pending_orders()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM pending_orders
    WHERE expires_at < NOW();
END;
$$;

-- Schedule cleanup to run every hour
-- Note: For Supabase, we'll use their built-in scheduled functions instead of pg_cron
-- You'll need to set this up in the Supabase dashboard under Database -> Database Functions
-- and then Schedule the function under Database -> Scheduled functions
-- For now, we'll keep the function ready for manual cleanup

-- Example of how to manually clean up expired orders:
-- SELECT cleanup_expired_pending_orders();

-- Note: To set up scheduled cleanup in Supabase:
-- 1. Go to Supabase Dashboard
-- 2. Navigate to Database -> Scheduled functions
-- 3. Click "Create new schedule"
-- 4. Set Schedule to: 0 * * * * (every hour)
-- 5. Use this SQL: SELECT cleanup_expired_pending_orders();
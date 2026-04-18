-- =====================================================
-- MIGRATION: Buyers Tables (Buyer-specific tables to differentiate from seller tables)
-- Run this in Supabase SQL Editor
-- =====================================================

-- =====================================================
-- 1. BUYERS_ORDERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS buyers_orders (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    order_number VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    subtotal DECIMAL(10,2) DEFAULT 0,
    shipping DECIMAL(10,2) DEFAULT 0,
    tax DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(10,2) DEFAULT 0,
    tracking_number VARCHAR(100),
    shipping_address TEXT,
    billing_address TEXT,
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE buyers_orders ENABLE ROW LEVEL SECURITY;

-- Policies for buyers_orders
CREATE POLICY "Buyers can view their own orders" ON buyers_orders 
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Buyers can create their own orders" ON buyers_orders 
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Buyers can update their own orders" ON buyers_orders 
    FOR UPDATE USING (auth.uid() = user_id);

-- =====================================================
-- 2. BUYERS_ORDER_ITEMS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS buyers_order_items (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    order_id UUID REFERENCES buyers_orders(id) ON DELETE CASCADE,
    product_id BIGINT REFERENCES products(id) ON DELETE SET NULL,
    seller_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    quantity INTEGER DEFAULT 1,
    price DECIMAL(10,2) DEFAULT 0,
    product_name VARCHAR(255),
    product_image TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE buyers_order_items ENABLE ROW LEVEL SECURITY;

-- Policies for buyers_order_items (users can see items for their orders)
CREATE POLICY "Buyers can view their own order items" ON buyers_order_items 
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM buyers_orders 
            WHERE buyers_orders.id = buyers_order_items.order_id 
            AND buyers_orders.user_id = auth.uid()
        )
    );

CREATE POLICY "Buyers can create order items for their orders" ON buyers_order_items 
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM buyers_orders 
            WHERE buyers_orders.id = buyers_order_items.order_id 
            AND buyers_orders.user_id = auth.uid()
        )
    );

-- =====================================================
-- 3. BUYERS_WISHLIST TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS buyers_wishlist (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);

-- Enable RLS
ALTER TABLE buyers_wishlist ENABLE ROW LEVEL SECURITY;

-- Policies for buyers_wishlist
CREATE POLICY "Buyers can view their own wishlist" ON buyers_wishlist 
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Buyers can add to their own wishlist" ON buyers_wishlist 
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Buyers can delete from their own wishlist" ON buyers_wishlist 
    FOR DELETE USING (auth.uid() = user_id);

-- =====================================================
-- 4. BUYERS_REVIEWS TABLE (for profile stats)
-- =====================================================
CREATE TABLE IF NOT EXISTS buyers_reviews (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    product_id BIGINT REFERENCES products(id) ON DELETE SET NULL,
    order_id UUID REFERENCES buyers_orders(id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    comment TEXT,
    images TEXT[],
    verified_purchase BOOLEAN DEFAULT false,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);

-- Enable RLS
ALTER TABLE buyers_reviews ENABLE ROW LEVEL SECURITY;

-- Policies for buyers_reviews
CREATE POLICY "Anyone can view reviews" ON buyers_reviews 
    FOR SELECT USING (true);

CREATE POLICY "Buyers can create their own reviews" ON buyers_reviews 
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Buyers can update their own reviews" ON buyers_reviews 
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Buyers can delete their own reviews" ON buyers_reviews 
    FOR DELETE USING (auth.uid() = user_id);

-- =====================================================
-- 5. BUYERS_NOTIFICATIONS TABLE (for settings page)
-- =====================================================
CREATE TABLE IF NOT EXISTS buyers_notifications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    type VARCHAR(50),
    title VARCHAR(255),
    message TEXT,
    data JSONB,
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE buyers_notifications ENABLE ROW LEVEL SECURITY;

-- Policies for buyers_notifications
CREATE POLICY "Buyers can view their own notifications" ON buyers_notifications 
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Buyers can update their own notifications" ON buyers_notifications 
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Buyers can delete their own notifications" ON buyers_notifications 
    FOR DELETE USING (auth.uid() = user_id);

-- =====================================================
-- 6. Create indexes for better performance
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_buyers_orders_user_id ON buyers_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_buyers_orders_status ON buyers_orders(status);
CREATE INDEX IF NOT EXISTS idx_buyers_orders_created_at ON buyers_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_buyers_order_items_order_id ON buyers_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_buyers_order_items_product_id ON buyers_order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_buyers_wishlist_user_id ON buyers_wishlist(user_id);
CREATE INDEX IF NOT EXISTS idx_buyers_wishlist_product_id ON buyers_wishlist(product_id);
CREATE INDEX IF NOT EXISTS idx_buyers_reviews_user_id ON buyers_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_buyers_reviews_product_id ON buyers_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_buyers_notifications_user_id ON buyers_notifications(user_id);

-- =====================================================
-- 7. Function to update updated_at timestamp
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_buyers_orders_updated_at ON buyers_orders;
CREATE TRIGGER update_buyers_orders_updated_at BEFORE UPDATE ON buyers_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_buyers_reviews_updated_at ON buyers_reviews;
CREATE TRIGGER update_buyers_reviews_updated_at BEFORE UPDATE ON buyers_reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- RESULT
-- =====================================================
SELECT 'Migration completed successfully! Buyer tables created: 
- buyers_orders
- buyers_order_items  
- buyers_wishlist
- buyers_reviews
- buyers_notifications' as result;

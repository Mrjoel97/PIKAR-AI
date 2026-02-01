-- Migration: 0008_commerce_schema.sql
-- Description: Schema for Products, Orders, Invoices, and Inventory

-- Products / Services
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    sku TEXT,
    price DECIMAL(10, 2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    type TEXT CHECK (type IN ('physical', 'digital', 'service')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Inventory (for physical products)
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 0,
    reserved INTEGER DEFAULT 0,
    location TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL, -- The seller (app user)
    customer_name TEXT,
    customer_email TEXT,
    status TEXT CHECK (status IN ('draft', 'pending', 'paid', 'shipped', 'cancelled', 'refunded')),
    total_amount DECIMAL(10, 2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Order Items
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    order_id UUID REFERENCES orders(id),
    invoice_number TEXT NOT NULL,
    status TEXT CHECK (status IN ('draft', 'sent', 'paid', 'overdue', 'void')),
    due_date DATE,
    pdf_url TEXT, -- Link to generated PDF in storage
    metadata JSONB DEFAULT '{}'::jsonb, -- Store OCR data here for uploaded invoices
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_user ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);

-- RLS
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Policies (Service Role has full access by default, but nice to be explicit)
DO $$ BEGIN
    CREATE POLICY "Service Role manages all" ON products USING (true) WITH CHECK (true);
    CREATE POLICY "Service Role manages all" ON inventory USING (true) WITH CHECK (true);
    CREATE POLICY "Service Role manages all" ON orders USING (true) WITH CHECK (true);
    CREATE POLICY "Service Role manages all" ON order_items USING (true) WITH CHECK (true);
    CREATE POLICY "Service Role manages all" ON invoices USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Triggers
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

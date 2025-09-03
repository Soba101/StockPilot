-- Initial database setup
-- First, create the stockpilot user if connecting as postgres
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'stockpilot') THEN
        CREATE ROLE stockpilot WITH LOGIN PASSWORD 'stockpilot_dev' SUPERUSER CREATEDB CREATEROLE;
    END IF;
END $$;

-- Continue setup as postgres since we're already connected to stockpilot database

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Locations table
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('warehouse', 'store', 'virtual')),
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Ensure unique location names per org
CREATE UNIQUE INDEX IF NOT EXISTS ux_locations_org_name ON locations(org_id, name);

-- Suppliers table (must come before products due to foreign key reference)
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    lead_time_days INTEGER DEFAULT 7,
    minimum_order_quantity INTEGER DEFAULT 1,
    payment_terms VARCHAR(100),
    is_active VARCHAR(10) DEFAULT 'true',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT chk_suppliers_is_active CHECK (is_active IN ('true', 'false'))
);

-- Products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    sku VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    cost DECIMAL(10,2),
    price DECIMAL(10,2),
    uom VARCHAR(20) DEFAULT 'each',
    reorder_point INTEGER DEFAULT 0,
    safety_stock_days INTEGER DEFAULT 3,
    preferred_supplier_id UUID REFERENCES suppliers(id),
    pack_size INTEGER DEFAULT 1,
    max_stock_days INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(org_id, sku)
);

-- Users table for auth
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('admin','viewer','purchaser')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Inventory movements table
CREATE TABLE inventory_movements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN ('in', 'out', 'adjust', 'transfer')),
    reference VARCHAR(255),
    notes TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID, -- Will reference users table when auth is implemented
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Orders table (for sales tracking)
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    order_number VARCHAR(100) NOT NULL,
    channel VARCHAR(50), -- 'online', 'pos', 'phone', etc.
    status VARCHAR(20) DEFAULT 'pending',
    ordered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fulfilled_at TIMESTAMP WITH TIME ZONE,
    location_id UUID REFERENCES locations(id),
    total_amount DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Order items table
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Purchase order status enum
DO $$ BEGIN
    CREATE TYPE purchase_order_status AS ENUM ('draft', 'pending', 'ordered', 'received', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Purchase orders table
CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    po_number VARCHAR(50) NOT NULL UNIQUE,
    status purchase_order_status DEFAULT 'draft',
    order_date TIMESTAMP WITH TIME ZONE,
    expected_date TIMESTAMP WITH TIME ZONE,
    received_date TIMESTAMP WITH TIME ZONE,
    total_amount FLOAT DEFAULT 0.0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID
);

-- Purchase order items table
CREATE TABLE purchase_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_order_id UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    unit_cost FLOAT NOT NULL,
    total_cost FLOAT NOT NULL,
    received_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_products_org_sku ON products(org_id, sku);
CREATE INDEX idx_inventory_movements_product ON inventory_movements(product_id);
CREATE INDEX idx_inventory_movements_location ON inventory_movements(location_id);
CREATE INDEX idx_inventory_movements_timestamp ON inventory_movements(timestamp);
CREATE INDEX idx_orders_org ON orders(org_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_purchase_orders_org ON purchase_orders(org_id);
CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_order_items_po ON purchase_order_items(purchase_order_id);

-- Insert sample organization for development
INSERT INTO organizations (name) VALUES ('Demo Company');

-- Get the org ID for sample data
DO $$
DECLARE
    demo_org_id UUID;
    warehouse_id UUID;
BEGIN
    SELECT id INTO demo_org_id FROM organizations WHERE name = 'Demo Company';
    
    -- Insert sample location
    INSERT INTO locations (org_id, name, type) 
    VALUES (demo_org_id, 'Main Warehouse', 'warehouse')
    RETURNING id INTO warehouse_id;
    
    -- Insert sample products
    INSERT INTO products (org_id, sku, name, category, cost, price, reorder_point) VALUES
    (demo_org_id, 'WIDGET-001', 'Blue Widget', 'Widgets', 5.00, 15.00, 10),
    (demo_org_id, 'WIDGET-002', 'Red Widget', 'Widgets', 5.50, 16.00, 8),
    (demo_org_id, 'GADGET-001', 'Super Gadget', 'Gadgets', 25.00, 75.00, 5);
    
    -- Insert sample suppliers
    INSERT INTO suppliers (org_id, name, contact_person, email, phone, lead_time_days, minimum_order_quantity) VALUES
    (demo_org_id, 'Acme Supply Co', 'John Smith', 'orders@acmesupply.com', '555-0123', 7, 10),
    (demo_org_id, 'Gizmo Corp', 'Jane Doe', 'purchasing@gizmocorp.com', '555-0456', 14, 5),
    (demo_org_id, 'Widget Works', 'Bob Johnson', 'sales@widgetworks.com', '555-0789', 10, 25);
    
    -- Insert demo admin user with properly hashed password
    -- Password: admin123 (hashed with bcrypt)
    INSERT INTO users (org_id, email, password_hash, role) VALUES
    (demo_org_id, 'admin@demo.co', '$2b$12$AfzHESO676gWQM8.pLwcpuHjOJ1/R4QcJKleU28/2O5iEqoSUXNHe', 'admin');
END $$;
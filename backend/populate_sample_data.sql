-- Comprehensive Sample Data for StockPilot
-- This script populates the database with realistic inventory management data

-- Clean existing data (except the demo org we'll expand)
DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM inventory_movements;
DELETE FROM products WHERE org_id IN (SELECT id FROM organizations WHERE name != 'Demo Company');
DELETE FROM locations WHERE org_id IN (SELECT id FROM organizations WHERE name != 'Demo Company');
DELETE FROM users WHERE org_id IN (SELECT id FROM organizations WHERE name != 'Demo Company');
DELETE FROM suppliers;
DELETE FROM organizations WHERE name != 'Demo Company';

-- Get demo org ID
DO $$
DECLARE
    demo_org_id UUID;
    tech_org_id UUID;
    main_warehouse_id UUID;
    retail_store_id UUID;
    online_center_id UUID;
    tech_warehouse_id UUID;
    tech_showroom_id UUID;
BEGIN
    -- Get demo org
    SELECT id INTO demo_org_id FROM organizations WHERE name = 'Demo Company';
    
    -- Create additional organizations
    INSERT INTO organizations (name) VALUES ('TechCorp Solutions') RETURNING id INTO tech_org_id;
    
    -- Clear existing demo data
    DELETE FROM inventory_movements WHERE product_id IN (SELECT id FROM products WHERE org_id = demo_org_id);
    DELETE FROM products WHERE org_id = demo_org_id;
    DELETE FROM locations WHERE org_id = demo_org_id;
    DELETE FROM users WHERE org_id = demo_org_id AND email != 'admin@demo.co';
    
    -- === DEMO COMPANY DATA ===
    
    -- Locations for Demo Company
    INSERT INTO locations (org_id, name, type, address) VALUES
    (demo_org_id, 'Main Warehouse', 'warehouse', '123 Industrial Blvd, Springfield, IL 62701')
    RETURNING id INTO main_warehouse_id;
    
    INSERT INTO locations (org_id, name, type, address) VALUES
    (demo_org_id, 'Retail Store Downtown', 'store', '456 Main St, Springfield, IL 62704'),
    (demo_org_id, 'Online Fulfillment Center', 'warehouse', '789 Commerce Way, Springfield, IL 62702');
    
    SELECT id INTO retail_store_id FROM locations WHERE name = 'Retail Store Downtown' AND org_id = demo_org_id;
    SELECT id INTO online_center_id FROM locations WHERE name = 'Online Fulfillment Center' AND org_id = demo_org_id;
    
    -- Products for Demo Company (Consumer Goods)
    INSERT INTO products (org_id, sku, name, description, category, cost, price, reorder_point) VALUES
    -- Electronics
    (demo_org_id, 'ELEC-001', 'Bluetooth Wireless Headphones', 'Premium over-ear headphones with noise cancellation', 'Electronics', 45.00, 129.99, 25),
    (demo_org_id, 'ELEC-002', 'USB-C Charging Cable 6ft', 'Fast charging USB-C to USB-A cable', 'Electronics', 3.50, 19.99, 100),
    (demo_org_id, 'ELEC-003', 'Portable Power Bank 10000mAh', 'High capacity portable charger with dual USB ports', 'Electronics', 18.00, 49.99, 50),
    (demo_org_id, 'ELEC-004', 'Wireless Phone Charger', 'Qi-compatible wireless charging pad', 'Electronics', 12.00, 34.99, 30),
    (demo_org_id, 'ELEC-005', 'Smart Fitness Tracker', 'Waterproof fitness band with heart rate monitor', 'Electronics', 25.00, 79.99, 20),
    
    -- Home & Garden
    (demo_org_id, 'HOME-001', 'Ceramic Coffee Mug Set', 'Set of 4 ceramic mugs with modern design', 'Home & Garden', 8.00, 24.99, 40),
    (demo_org_id, 'HOME-002', 'Stainless Steel Water Bottle', '32oz insulated water bottle', 'Home & Garden', 12.00, 29.99, 60),
    (demo_org_id, 'HOME-003', 'LED Desk Lamp', 'Adjustable LED desk lamp with USB charging port', 'Home & Garden', 22.00, 59.99, 15),
    (demo_org_id, 'HOME-004', 'Indoor Plant Starter Kit', 'Includes pots, soil, and seeds for herbs', 'Home & Garden', 15.00, 39.99, 25),
    (demo_org_id, 'HOME-005', 'Bamboo Cutting Board Set', 'Set of 3 bamboo cutting boards', 'Home & Garden', 20.00, 49.99, 20),
    
    -- Sports & Outdoors
    (demo_org_id, 'SPORT-001', 'Yoga Mat Premium', 'Non-slip yoga mat with carrying strap', 'Sports & Outdoors', 18.00, 44.99, 35),
    (demo_org_id, 'SPORT-002', 'Resistance Band Set', 'Set of 5 resistance bands with handles', 'Sports & Outdoors', 12.00, 29.99, 50),
    (demo_org_id, 'SPORT-003', 'Insulated Sports Water Bottle', '24oz stainless steel sports bottle', 'Sports & Outdoors', 14.00, 34.99, 45),
    (demo_org_id, 'SPORT-004', 'Foam Roller', 'High-density foam roller for muscle recovery', 'Sports & Outdoors', 16.00, 39.99, 30),
    (demo_org_id, 'SPORT-005', 'Adjustable Dumbbells', 'Pair of adjustable dumbbells 5-25 lbs', 'Sports & Outdoors', 65.00, 149.99, 10),
    
    -- Office Supplies
    (demo_org_id, 'OFF-001', 'Ergonomic Mouse Pad', 'Gel wrist support mouse pad', 'Office', 8.00, 19.99, 75),
    (demo_org_id, 'OFF-002', 'Wireless Keyboard', 'Compact wireless keyboard with number pad', 'Office', 35.00, 79.99, 20),
    (demo_org_id, 'OFF-003', 'Notebook Set', 'Set of 3 lined notebooks', 'Office', 6.00, 14.99, 80),
    (demo_org_id, 'OFF-004', 'Desk Organizer', 'Bamboo desk organizer with compartments', 'Office', 18.00, 39.99, 25),
    (demo_org_id, 'OFF-005', 'Blue Light Glasses', 'Computer glasses to reduce eye strain', 'Office', 15.00, 34.99, 40);
    
    -- === TECHCORP SOLUTIONS DATA ===
    
    -- Locations for TechCorp
    INSERT INTO locations (org_id, name, type, address) VALUES
    (tech_org_id, 'Tech Warehouse', 'warehouse', '100 Silicon Valley Dr, San Jose, CA 95110')
    RETURNING id INTO tech_warehouse_id;
    
    INSERT INTO locations (org_id, name, type, address) VALUES
    (tech_org_id, 'Showroom & Demo Center', 'store', '200 Innovation Blvd, San Francisco, CA 94107');
    
    SELECT id INTO tech_showroom_id FROM locations WHERE name = 'Showroom & Demo Center' AND org_id = tech_org_id;
    
    -- Products for TechCorp (B2B Tech)
    INSERT INTO products (org_id, sku, name, description, category, cost, price, reorder_point) VALUES
    -- Networking Equipment
    (tech_org_id, 'NET-001', 'Enterprise Router Pro', '24-port gigabit enterprise router', 'Networking', 450.00, 1299.99, 5),
    (tech_org_id, 'NET-002', 'Managed Switch 48-Port', '48-port managed ethernet switch', 'Networking', 320.00, 899.99, 8),
    (tech_org_id, 'NET-003', 'Wireless Access Point', 'Enterprise-grade WiFi 6 access point', 'Networking', 180.00, 449.99, 15),
    (tech_org_id, 'NET-004', 'Network Cable Cat6 1000ft', 'Cat6 ethernet cable bulk roll', 'Networking', 65.00, 149.99, 20),
    (tech_org_id, 'NET-005', 'Firewall Appliance', 'Next-gen firewall with VPN support', 'Networking', 800.00, 2199.99, 3),
    
    -- Servers & Storage
    (tech_org_id, 'SRV-001', 'Rack Server 2U', '2U rackmount server with dual CPUs', 'Servers', 1200.00, 3499.99, 4),
    (tech_org_id, 'SRV-002', 'NAS Storage 8-Bay', '8-bay network attached storage', 'Servers', 650.00, 1799.99, 6),
    (tech_org_id, 'SRV-003', 'UPS Power Supply', '2000VA uninterruptible power supply', 'Servers', 180.00, 499.99, 10),
    (tech_org_id, 'SRV-004', 'Server Memory 32GB', '32GB DDR4 ECC server memory', 'Servers', 220.00, 599.99, 25),
    (tech_org_id, 'SRV-005', 'SSD Enterprise 2TB', '2TB enterprise SSD drive', 'Servers', 380.00, 899.99, 15);
    
    -- Users for both organizations
    INSERT INTO users (org_id, email, password_hash, role) VALUES
    -- Demo Company users
    (demo_org_id, 'viewer@demo.co', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.Ge', 'viewer'),
    (demo_org_id, 'purchaser@demo.co', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.Ge', 'purchaser'),
    -- TechCorp users
    (tech_org_id, 'admin@techcorp.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.Ge', 'admin'),
    (tech_org_id, 'operations@techcorp.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5u.Ge', 'purchaser');
    
    -- Suppliers
    INSERT INTO suppliers (org_id, name, contact_email, contact_phone, lead_time_days, minimum_order_quantity) VALUES
    -- Demo Company suppliers
    (demo_org_id, 'Global Electronics Ltd', 'orders@globalelec.com', '+1-555-0101', 14, 50),
    (demo_org_id, 'Home Essentials Co', 'sales@homeessentials.com', '+1-555-0102', 7, 25),
    (demo_org_id, 'Sports Gear Direct', 'purchasing@sportsgear.com', '+1-555-0103', 10, 20),
    (demo_org_id, 'Office Plus Supply', 'b2b@officeplus.com', '+1-555-0104', 5, 100),
    -- TechCorp suppliers
    (tech_org_id, 'Enterprise Tech Distributors', 'sales@enterpisetech.com', '+1-555-0201', 21, 1),
    (tech_org_id, 'Network Solutions Inc', 'orders@netsolutions.com', '+1-555-0202', 14, 5),
    (tech_org_id, 'Server Components Direct', 'b2b@servercomponents.com', '+1-555-0203', 28, 1);
    
    -- === INITIAL INVENTORY MOVEMENTS ===
    
    -- Demo Company - Stock incoming movements
    INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp) 
    SELECT p.id, main_warehouse_id, 
           CASE 
               WHEN p.category = 'Electronics' THEN 100 + (RANDOM() * 50)::INTEGER
               WHEN p.category = 'Office' THEN 150 + (RANDOM() * 100)::INTEGER
               ELSE 75 + (RANDOM() * 75)::INTEGER
           END,
           'in', 
           'PO-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 6, '0'),
           'Initial stock receipt',
           NOW() - INTERVAL '90 days' + (RANDOM() * INTERVAL '60 days')
    FROM products p WHERE p.org_id = demo_org_id;
    
    -- Demo Company - Distribute to retail store (30% of warehouse stock)
    INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp)
    SELECT p.id, retail_store_id,
           (im.quantity * 0.3)::INTEGER,
           'in',
           'TRANSFER-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 6, '0'),
           'Transfer from main warehouse',
           im.timestamp + INTERVAL '2 days'
    FROM products p
    JOIN inventory_movements im ON p.id = im.product_id AND im.location_id = main_warehouse_id
    WHERE p.org_id = demo_org_id;
    
    -- Demo Company - Corresponding outbound from warehouse
    INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp)
    SELECT p.id, main_warehouse_id,
           -(im_in.quantity),
           'out',
           'TRANSFER-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 6, '0'),
           'Transfer to retail store',
           im_in.timestamp
    FROM products p
    JOIN inventory_movements im_in ON p.id = im_in.product_id AND im_in.location_id = retail_store_id
    WHERE p.org_id = demo_org_id AND im_in.movement_type = 'in' AND im_in.reference LIKE 'TRANSFER-%';
    
    -- Demo Company - Online fulfillment center stock (20% of warehouse)
    INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp)
    SELECT p.id, online_center_id,
           (im.quantity * 0.2)::INTEGER,
           'in',
           'TRANSFER-OFC-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 6, '0'),
           'Transfer to online fulfillment',
           im.timestamp + INTERVAL '3 days'
    FROM products p
    JOIN inventory_movements im ON p.id = im.product_id AND im.location_id = main_warehouse_id AND im.movement_type = 'in'
    WHERE p.org_id = demo_org_id;
    
    -- Demo Company - Corresponding outbound from warehouse
    INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp)
    SELECT p.id, main_warehouse_id,
           -(im_in.quantity),
           'out',
           'TRANSFER-OFC-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 6, '0'),
           'Transfer to online fulfillment',
           im_in.timestamp
    FROM products p
    JOIN inventory_movements im_in ON p.id = im_in.product_id AND im_in.location_id = online_center_id
    WHERE p.org_id = demo_org_id AND im_in.movement_type = 'in' AND im_in.reference LIKE 'TRANSFER-OFC-%';
    
    -- TechCorp - Initial stock
    INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp) 
    SELECT p.id, tech_warehouse_id, 
           CASE 
               WHEN p.category = 'Networking' THEN 15 + (RANDOM() * 25)::INTEGER
               WHEN p.category = 'Servers' THEN 8 + (RANDOM() * 15)::INTEGER
               ELSE 20 + (RANDOM() * 30)::INTEGER
           END,
           'in', 
           'PO-TECH-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 4, '0'),
           'Initial inventory setup',
           NOW() - INTERVAL '60 days' + (RANDOM() * INTERVAL '30 days')
    FROM products p WHERE p.org_id = tech_org_id;
    
    -- TechCorp - Demo center stock (smaller quantities)
    INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp)
    SELECT p.id, tech_showroom_id,
           LEAST(im.quantity * 0.15, 3)::INTEGER,
           'in',
           'DEMO-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 4, '0'),
           'Demo center allocation',
           im.timestamp + INTERVAL '1 day'
    FROM products p
    JOIN inventory_movements im ON p.id = im.product_id AND im.location_id = tech_warehouse_id
    WHERE p.org_id = tech_org_id AND im.quantity > 5;
    
    -- === SALES ORDERS ===
    
    -- Demo Company Orders
    INSERT INTO orders (org_id, order_number, channel, status, ordered_at, fulfilled_at, location_id, total_amount) VALUES
    (demo_org_id, 'ORD-2024-001', 'online', 'fulfilled', NOW() - INTERVAL '30 days', NOW() - INTERVAL '28 days', online_center_id, 189.97),
    (demo_org_id, 'ORD-2024-002', 'pos', 'fulfilled', NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days', retail_store_id, 94.98),
    (demo_org_id, 'ORD-2024-003', 'online', 'fulfilled', NOW() - INTERVAL '20 days', NOW() - INTERVAL '18 days', online_center_id, 229.96),
    (demo_org_id, 'ORD-2024-004', 'phone', 'pending', NOW() - INTERVAL '3 days', NULL, main_warehouse_id, 159.98),
    (demo_org_id, 'ORD-2024-005', 'pos', 'fulfilled', NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days', retail_store_id, 79.99);
    
    -- TechCorp Orders 
    INSERT INTO orders (org_id, order_number, channel, status, ordered_at, fulfilled_at, location_id, total_amount) VALUES
    (tech_org_id, 'TECH-001', 'online', 'fulfilled', NOW() - INTERVAL '45 days', NOW() - INTERVAL '23 days', tech_warehouse_id, 4599.97),
    (tech_org_id, 'TECH-002', 'phone', 'fulfilled', NOW() - INTERVAL '35 days', NOW() - INTERVAL '21 days', tech_warehouse_id, 2699.98),
    (tech_org_id, 'TECH-003', 'online', 'pending', NOW() - INTERVAL '7 days', NULL, tech_warehouse_id, 1799.99);
    
END $$;

-- Insert order items for the orders
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.id, p.id, 
       CASE WHEN p.price < 50 THEN 2 + (RANDOM() * 3)::INTEGER ELSE 1 END,
       p.price
FROM orders o
JOIN organizations org ON o.org_id = org.id  
JOIN products p ON p.org_id = org.id
WHERE o.order_number IN ('ORD-2024-001', 'ORD-2024-002', 'ORD-2024-003', 'ORD-2024-005', 'TECH-001', 'TECH-002')
  AND (RANDOM() < 0.3); -- 30% chance each product is in an order

-- Add corresponding sales movements (outbound)
INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp, created_at)
SELECT oi.product_id, o.location_id, -oi.quantity, 'out', o.order_number, 'Sales order fulfillment', o.fulfilled_at, o.fulfilled_at
FROM order_items oi
JOIN orders o ON oi.order_id = o.id
WHERE o.status = 'fulfilled';

-- Add some stock adjustments (cycle counts)
INSERT INTO inventory_movements (product_id, location_id, quantity, movement_type, reference, notes, timestamp)
SELECT p.id, l.id, 
       (RANDOM() * 6 - 3)::INTEGER, -- Random adjustment between -3 and +3
       'adjust',
       'ADJ-' || EXTRACT(MONTH FROM NOW()) || '-' || LPAD((ROW_NUMBER() OVER ())::TEXT, 3, '0'),
       'Cycle count adjustment',
       NOW() - INTERVAL '7 days' + (RANDOM() * INTERVAL '7 days')
FROM products p
JOIN locations l ON l.org_id = p.org_id
WHERE RANDOM() < 0.2; -- 20% of product-location combinations get adjustments

-- Summary report
DO $$
DECLARE
    org_count INTEGER;
    location_count INTEGER;
    product_count INTEGER;
    movement_count INTEGER;
    user_count INTEGER;
    order_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO org_count FROM organizations;
    SELECT COUNT(*) INTO location_count FROM locations;
    SELECT COUNT(*) INTO product_count FROM products;
    SELECT COUNT(*) INTO movement_count FROM inventory_movements;
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO order_count FROM orders;
    
    RAISE NOTICE '=== DATABASE POPULATION COMPLETE ===';
    RAISE NOTICE 'Organizations: %', org_count;
    RAISE NOTICE 'Locations: %', location_count;
    RAISE NOTICE 'Products: %', product_count;
    RAISE NOTICE 'Inventory Movements: %', movement_count;
    RAISE NOTICE 'Users: %', user_count;
    RAISE NOTICE 'Orders: %', order_count;
    RAISE NOTICE '====================================';
END $$;
#!/usr/bin/env python3
"""
Generate 5 years of realistic data for TechFlow Solutions
IT Equipment Distributor - Aug 14, 2020 to Aug 13, 2025
Includes COVID impact, supply chain issues, and tech industry patterns
"""

import os
import sys
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import math

# Simple Poisson approximation
def poisson_approx(lam):
    """Approximate Poisson distribution for reasonable lambda values"""
    if lam <= 0:
        return 0
    elif lam < 10:
        L = math.exp(-lam)
        k = 0
        p = 1
        while p > L:
            k += 1
            p *= random.random()
        return k - 1
    else:
        return max(0, int(random.gauss(lam, math.sqrt(lam)) + 0.5))

@dataclass
class Product:
    id: str
    org_id: str
    sku: str
    name: str
    cost: float
    price: float
    category: str
    subcategory: str
    reorder_point: int
    base_velocity: float = 2.0
    covid_impact_factor: float = 1.0  # How COVID affected this product
    supply_chain_risk: float = 0.1    # Likelihood of supply issues

@dataclass
class Location:
    id: str
    org_id: str
    name: str
    type: str
    
class TechFlowDataGenerator:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None
        # 5 years: Aug 14, 2020 to Aug 13, 2025
        self.start_date = datetime(2020, 8, 14, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 8, 13, 23, 59, 59, tzinfo=timezone.utc)
        self.products: List[Product] = []
        self.locations: List[Location] = []
        self.techflow_org_id = None
        
        # Historical periods for modeling
        self.covid_lockdown_start = datetime(2020, 3, 15, tzinfo=timezone.utc)
        self.covid_recovery_start = datetime(2021, 6, 1, tzinfo=timezone.utc)
        self.supply_shortage_peak = datetime(2021, 10, 1, tzinfo=timezone.utc)
        self.normalization_start = datetime(2022, 6, 1, tzinfo=timezone.utc)
        
    def connect(self):
        """Connect to database"""
        self.conn = psycopg2.connect(self.db_url)
        self.conn.autocommit = True
        print("Connected to database")
    
    def disconnect(self):
        if self.conn:
            self.conn.close()
    
    def setup_techflow_business(self):
        """Create TechFlow Solutions organization with realistic setup"""
        print("Setting up TechFlow Solutions business...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Clear existing data in correct order (foreign key constraints)
            cur.execute("DELETE FROM purchase_order_items")
            cur.execute("DELETE FROM purchase_orders")
            cur.execute("DELETE FROM order_items")
            cur.execute("DELETE FROM orders")
            cur.execute("DELETE FROM inventory_movements")
            cur.execute("DELETE FROM products")
            cur.execute("DELETE FROM suppliers")
            cur.execute("DELETE FROM users")
            cur.execute("DELETE FROM locations")
            cur.execute("DELETE FROM organizations")
            
            # Create TechFlow Solutions organization
            cur.execute("""
                INSERT INTO organizations (name) 
                VALUES ('TechFlow Solutions Inc.')
                RETURNING id
            """)
            self.techflow_org_id = str(cur.fetchone()['id'])
            
            # Create locations
            locations_data = [
                ('Main Warehouse', 'warehouse', '2500 Tech Center Dr, Austin, TX 78759'),
                ('East Coast Distribution', 'warehouse', '1200 Industrial Blvd, Atlanta, GA 30309'),
                ('West Coast Hub', 'warehouse', '800 Logistics Way, San Jose, CA 95110'),
                ('Customer Service Center', 'store', '100 Business Park Dr, Austin, TX 78759'),
            ]
            
            for name, loc_type, address in locations_data:
                cur.execute("""
                    INSERT INTO locations (org_id, name, type, address)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (self.techflow_org_id, name, loc_type, address))
                
                location_id = str(cur.fetchone()['id'])
                self.locations.append(Location(location_id, self.techflow_org_id, name, loc_type))
            
            # Create comprehensive product catalog
            self.create_product_catalog(cur)
            
            # Create suppliers
            self.create_suppliers(cur)
            
            # Create users
            self.create_users(cur)
            
        print(f"Created TechFlow Solutions with {len(self.products)} products and {len(self.locations)} locations")
    
    def create_product_catalog(self, cur):
        """Create realistic IT product catalog"""
        
        # Product categories with realistic pricing and velocity patterns
        product_catalog = [
            # Laptops - High value, moderate velocity, COVID boost
            ('LAP-001', 'Dell Latitude 7420 14" Business Laptop', 'Laptops', 'Business', 1299.99, 1899.99, 8, 1.2, 2.5),
            ('LAP-002', 'HP EliteBook 850 G8 15" Laptop', 'Laptops', 'Business', 1199.99, 1749.99, 6, 1.0, 2.8),
            ('LAP-003', 'Lenovo ThinkPad X1 Carbon Gen 9', 'Laptops', 'Premium', 1599.99, 2299.99, 4, 0.8, 3.2),
            ('LAP-004', 'Apple MacBook Air M2 13"', 'Laptops', 'Creative', 1099.99, 1599.99, 5, 0.9, 2.0),
            ('LAP-005', 'ASUS VivoBook 15.6" Budget', 'Laptops', 'Budget', 449.99, 699.99, 12, 1.5, 1.8),
            ('LAP-006', 'MSI Gaming Laptop GF65 Thin', 'Laptops', 'Gaming', 899.99, 1299.99, 6, 0.7, 2.2),
            
            # Monitors - Steady demand, WFH boost
            ('MON-001', 'Dell UltraSharp 24" 1440p Monitor', 'Monitors', 'Professional', 249.99, 379.99, 20, 2.2, 1.5),
            ('MON-002', 'LG 27" 4K USB-C Monitor', 'Monitors', 'Premium', 449.99, 649.99, 12, 1.8, 1.2),
            ('MON-003', 'ASUS 21.5" 1080p Budget Monitor', 'Monitors', 'Budget', 89.99, 149.99, 35, 3.5, 1.0),
            ('MON-004', 'Samsung 32" Curved Gaming Monitor', 'Monitors', 'Gaming', 349.99, 499.99, 15, 1.2, 0.8),
            ('MON-005', 'HP 24" Business Monitor with Stand', 'Monitors', 'Business', 179.99, 269.99, 25, 2.8, 1.3),
            
            # Networking - B2B focus, supply chain sensitive
            ('NET-001', 'Cisco Meraki MX64 Security Appliance', 'Networking', 'Enterprise', 449.99, 799.99, 8, 0.9, 2.8),
            ('NET-002', 'Ubiquiti UniFi Dream Machine Pro', 'Networking', 'SMB', 329.99, 499.99, 12, 1.1, 2.2),
            ('NET-003', 'NETGEAR ProSafe 24-Port Switch', 'Networking', 'Business', 199.99, 329.99, 15, 1.3, 1.8),
            ('NET-004', 'TP-Link Omada WiFi 6 Access Point', 'Networking', 'SMB', 129.99, 199.99, 25, 1.8, 1.5),
            ('NET-005', 'Aruba 2930F 48-Port Managed Switch', 'Networking', 'Enterprise', 899.99, 1399.99, 5, 0.6, 3.5),
            
            # Desktop Computers - B2B focus, various price points
            ('DT-001', 'Dell OptiPlex 7090 Small Form Factor', 'Desktops', 'Business', 649.99, 999.99, 10, 1.1, 2.0),
            ('DT-002', 'HP EliteDesk 800 G8 Mini PC', 'Desktops', 'Business', 599.99, 899.99, 12, 1.2, 1.8),
            ('DT-003', 'Lenovo ThinkCentre M90n Nano', 'Desktops', 'Compact', 499.99, 749.99, 15, 1.4, 1.5),
            ('DT-004', 'Custom Workstation - CAD/Engineering', 'Desktops', 'Workstation', 1899.99, 2799.99, 3, 0.4, 4.0),
            
            # Accessories - High velocity, lower margins
            ('ACC-001', 'Logitech MX Master 3 Wireless Mouse', 'Accessories', 'Input', 69.99, 99.99, 50, 4.2, 0.8),
            ('ACC-002', 'Dell Wireless Keyboard KB216', 'Accessories', 'Input', 24.99, 39.99, 75, 5.5, 0.5),
            ('ACC-003', 'Anker USB-C Hub 7-in-1', 'Accessories', 'Connectivity', 39.99, 59.99, 60, 3.8, 1.2),
            ('ACC-004', 'Cable Matters USB-C to HDMI 6ft', 'Accessories', 'Cables', 19.99, 29.99, 100, 6.2, 0.6),
            ('ACC-005', 'Belkin Surge Protector 12-Outlet', 'Accessories', 'Power', 49.99, 74.99, 40, 2.8, 0.9),
            ('ACC-006', 'Kensington Laptop Lock Security Cable', 'Accessories', 'Security', 34.99, 54.99, 35, 2.1, 0.7),
            
            # Software - High margin, license-based
            ('SW-001', 'Microsoft Office 365 Business Premium', 'Software', 'Productivity', 180.00, 264.00, 25, 2.5, 0.3),
            ('SW-002', 'Adobe Creative Suite Business License', 'Software', 'Creative', 599.99, 839.99, 8, 1.2, 0.2),
            ('SW-003', 'Symantec Endpoint Protection', 'Software', 'Security', 89.99, 139.99, 20, 1.8, 0.1),
            ('SW-004', 'QuickBooks Desktop Pro', 'Software', 'Accounting', 349.99, 499.99, 12, 1.1, 0.1),
            
            # Storage - Supply chain sensitive, various speeds
            ('STO-001', 'Samsung 980 PRO 1TB NVMe SSD', 'Storage', 'SSD', 119.99, 179.99, 30, 2.4, 2.1),
            ('STO-002', 'WD Blue 2TB SATA HDD', 'Storage', 'HDD', 54.99, 84.99, 45, 3.1, 1.8),
            ('STO-003', 'Seagate Barracuda 4TB Enterprise HDD', 'Storage', 'Enterprise', 129.99, 199.99, 25, 1.9, 2.5),
            ('STO-004', 'Kingston 32GB USB 3.0 Flash Drive', 'Storage', 'Portable', 12.99, 19.99, 80, 4.8, 0.8),
            
            # Servers - Low velocity, high value, long sales cycles
            ('SRV-001', 'Dell PowerEdge R750 2U Rack Server', 'Servers', 'Rack', 3999.99, 5999.99, 2, 0.3, 5.2),
            ('SRV-002', 'HPE ProLiant DL380 Gen10 Plus', 'Servers', 'Enterprise', 4299.99, 6299.99, 1, 0.2, 6.1),
            ('SRV-003', 'Synology DS1621+ 6-Bay NAS', 'Servers', 'Storage', 699.99, 999.99, 5, 0.8, 2.8),
        ]
        
        for sku, name, category, subcategory, cost, price, reorder_point, base_velocity, covid_factor in product_catalog:
            # Determine supply chain risk based on category
            supply_risk = {
                'Laptops': 0.25,      # High chip dependency
                'Monitors': 0.20,     # Display panel shortages  
                'Networking': 0.30,   # Complex chip requirements
                'Desktops': 0.22,     # Similar to laptops
                'Accessories': 0.10,  # Simpler components
                'Software': 0.05,     # Mostly digital
                'Storage': 0.28,      # Memory chip shortages
                'Servers': 0.35,      # Most complex supply chains
            }.get(category, 0.15)
            
            cur.execute("""
                INSERT INTO products (org_id, sku, name, description, category, cost, price, reorder_point)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                self.techflow_org_id, sku, name, 
                f"{subcategory} - {name}", category,
                cost, price, reorder_point
            ))
            
            product_id = str(cur.fetchone()['id'])
            
            self.products.append(Product(
                id=product_id,
                org_id=self.techflow_org_id,
                sku=sku,
                name=name,
                cost=cost,
                price=price,
                category=category,
                subcategory=subcategory,
                reorder_point=reorder_point,
                base_velocity=base_velocity,
                covid_impact_factor=covid_factor,
                supply_chain_risk=supply_risk
            ))
    
    def create_suppliers(self, cur):
        """Create realistic IT suppliers"""
        # First check what columns exist in suppliers table
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'suppliers' AND table_schema = 'public'
        """)
        columns = [row['column_name'] for row in cur.fetchall()]
        print(f"Available suppliers columns: {columns}")
        
        suppliers_data = [
            ('Dell Technologies', 'orders@dell.com', '+1-800-915-3355', 5, 5),
            ('HP Inc.', 'b2b@hp.com', '+1-800-752-0900', 7, 10),
            ('Lenovo Group', 'enterprise@lenovo.com', '+1-855-253-6686', 10, 3),
            ('Apple Inc.', 'business@apple.com', '+1-800-854-3680', 14, 1),
            ('ASUS', 'business@asus.com', '+1-888-678-3688', 12, 5),
            ('Microsoft Corporation', 'licensing@microsoft.com', '+1-800-642-7676', 1, 1),
            ('Cisco Systems', 'orders@cisco.com', '+1-800-553-6387', 8, 5),
            ('Ubiquiti Networks', 'sales@ubnt.com', '+1-408-942-4560', 6, 10),
            ('Samsung Electronics', 'b2b@samsung.com', '+1-800-726-7864', 9, 10),
            ('Western Digital', 'enterprise@wdc.com', '+1-800-275-4932', 7, 25),
            ('Seagate Technology', 'sales@seagate.com', '+1-800-732-4283', 8, 20),
            ('Kingston Technology', 'sales@kingston.com', '+1-714-435-2600', 5, 50),
            ('Logitech International', 'business@logitech.com', '+1-646-454-3200', 4, 25),
            ('Belkin International', 'wholesale@belkin.com', '+1-800-223-5546', 6, 20),
        ]
        
        for name, email, phone, lead_time, moq in suppliers_data:
            # Build INSERT dynamically based on available columns
            if 'contact_email' in columns and 'contact_phone' in columns:
                cur.execute("""
                    INSERT INTO suppliers (org_id, name, contact_email, contact_phone, lead_time_days, minimum_order_quantity)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (self.techflow_org_id, name, email, phone, lead_time, moq))
            elif 'contact_email' in columns:
                cur.execute("""
                    INSERT INTO suppliers (org_id, name, contact_email, lead_time_days, minimum_order_quantity)
                    VALUES (%s, %s, %s, %s, %s)
                """, (self.techflow_org_id, name, email, lead_time, moq))
            else:
                # Minimal version - just required fields
                cur.execute("""
                    INSERT INTO suppliers (org_id, name, lead_time_days, minimum_order_quantity)
                    VALUES (%s, %s, %s, %s)
                """, (self.techflow_org_id, name, lead_time, moq))
        
        print(f"Created {len(suppliers_data)} suppliers")
    
    def create_users(self, cur):
        """Create realistic users for the organization"""
        # Import password hashing (simplified for demo)
        import hashlib
        
        users_data = [
            ('admin@techflow.com', 'admin', 'System Administrator'),
            ('purchasing@techflow.com', 'purchaser', 'Sarah Johnson - Purchasing Manager'),  
            ('warehouse@techflow.com', 'admin', 'Mike Rodriguez - Warehouse Manager'),
            ('sales@techflow.com', 'viewer', 'Jennifer Chen - Sales Representative'),
            ('inventory@techflow.com', 'purchaser', 'David Kim - Inventory Analyst'),
            ('support@techflow.com', 'viewer', 'Lisa Brown - Customer Support'),
        ]
        
        for email, role, full_name in users_data:
            # Simple password hash (use proper bcrypt in production)
            password_hash = hashlib.sha256(f"password123_{email}".encode()).hexdigest()
            
            cur.execute("""
                INSERT INTO users (org_id, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
            """, (self.techflow_org_id, email, password_hash, role))
        
        print(f"Created {len(users_data)} users")
    
    def get_market_conditions(self, date: datetime) -> Dict[str, float]:
        """Get market condition multipliers for a specific date"""
        conditions = {
            'demand_multiplier': 1.0,
            'supply_reliability': 1.0,
            'price_inflation': 1.0
        }
        
        # COVID-19 Impact Timeline
        if self.covid_lockdown_start <= date < self.covid_recovery_start:
            # March 2020 - June 2021: Remote work surge
            conditions['demand_multiplier'] = 1.8  # Huge WFH equipment demand
            conditions['supply_reliability'] = 0.7  # Early supply disruptions
            
        elif self.covid_recovery_start <= date < self.supply_shortage_peak:
            # June 2021 - Oct 2021: Recovery but supply issues
            conditions['demand_multiplier'] = 1.4  # Still elevated demand
            conditions['supply_reliability'] = 0.5  # Worst supply shortages
            conditions['price_inflation'] = 1.2    # Price increases
            
        elif self.supply_shortage_peak <= date < self.normalization_start:
            # Oct 2021 - June 2022: Continued challenges
            conditions['demand_multiplier'] = 1.2  # Normalizing demand
            conditions['supply_reliability'] = 0.6  # Improving supply
            conditions['price_inflation'] = 1.3    # Peak inflation
            
        elif date >= self.normalization_start:
            # June 2022+: Recovery and normalization
            years_since = (date - self.normalization_start).days / 365.25
            # Gradual return to normal
            conditions['demand_multiplier'] = max(1.0, 1.2 - (years_since * 0.1))
            conditions['supply_reliability'] = min(1.0, 0.6 + (years_since * 0.2))
            conditions['price_inflation'] = max(1.0, 1.3 - (years_since * 0.15))
        
        return conditions
    
    def get_seasonal_multiplier(self, date: datetime, category: str) -> float:
        """Calculate seasonal demand patterns for tech products"""
        day_of_year = date.timetuple().tm_yday
        month = date.month
        
        # Tech industry patterns
        base_seasonal = 1.0
        
        # Back-to-school surge (July-September)
        if 180 <= day_of_year <= 270:  # July-September
            base_seasonal *= 1.3
        
        # Q4 business spending (October-November)
        if 270 <= day_of_year <= 330:  # Oct-Nov
            base_seasonal *= 1.2
        
        # Holiday slowdown (December)
        if 330 <= day_of_year <= 365:  # December
            base_seasonal *= 0.8
        
        # Q1 budget cycle (January-February)
        if 1 <= day_of_year <= 60:  # Jan-Feb
            base_seasonal *= 1.1
        
        # Category-specific patterns
        if category == 'Laptops':
            # Strong back-to-school
            if 210 <= day_of_year <= 250:  # Late July - Early Sept
                base_seasonal *= 1.4
        elif category == 'Servers':
            # End of fiscal year (Q4 for many companies)
            if 270 <= day_of_year <= 300:  # Oct-Nov
                base_seasonal *= 1.8
        elif category == 'Software':
            # License renewals in Jan and midyear
            if 1 <= day_of_year <= 31 or 180 <= day_of_year <= 210:
                base_seasonal *= 1.3
        
        return base_seasonal
    
    def generate_initial_inventory(self):
        """Generate realistic starting inventory levels"""
        print("Generating initial inventory (Aug 2020)...")
        
        movements = []
        main_warehouse = next((loc for loc in self.locations if 'Main Warehouse' in loc.name), self.locations[0])
        
        for product in self.products:
            # Initial stock varies by category and reorder patterns
            if product.category in ['Servers', 'Networking']:
                # Lower stock for high-value, low-velocity items
                stock = random.randint(product.reorder_point, product.reorder_point * 2)
            elif product.category in ['Accessories', 'Storage']:
                # Higher stock for fast-moving items
                stock = random.randint(product.reorder_point * 2, product.reorder_point * 4)
            else:
                # Standard stock levels
                stock = random.randint(product.reorder_point * 1, product.reorder_point * 3)
            
            movements.append((
                str(uuid.uuid4()),
                product.id,
                main_warehouse.id,
                stock,
                'in',
                self.start_date,
                'Initial inventory setup'
            ))
        
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO inventory_movements 
                (id, product_id, location_id, quantity, movement_type, timestamp, notes)
                VALUES %s
            """, movements)
        
        print(f"Created initial inventory for {len(movements)} products")
    
    def generate_daily_data(self, date: datetime):
        """Generate realistic daily business activity"""
        market_conditions = self.get_market_conditions(date)
        is_weekend = date.weekday() >= 5
        is_holiday = self.is_holiday(date)
        
        # B2B business - very limited weekend/holiday activity
        if is_weekend or is_holiday:
            # Only emergency orders or online self-service
            base_order_rate = 0.2
        else:
            base_order_rate = 1.0
        
        orders = []
        order_items = []
        movements = []
        
        # Determine daily order volume (seasonal + market conditions)
        base_daily_orders = 12  # Typical B2B distributor
        seasonal_mult = sum(self.get_seasonal_multiplier(date, cat) 
                          for cat in ['Laptops', 'Monitors', 'Networking', 'Servers']) / 4
        
        adjusted_orders = base_daily_orders * base_order_rate * seasonal_mult * market_conditions['demand_multiplier']
        num_orders = max(0, poisson_approx(adjusted_orders))
        
        # Generate orders
        for order_num in range(num_orders):
            order_data = self.generate_realistic_order(date, order_num + 1, market_conditions)
            if order_data:
                orders.append(order_data['order'])
                order_items.extend(order_data['items'])
                movements.extend(order_data['movements'])
        
        # Generate purchase orders and restocking based on market conditions
        po_data = self.generate_purchase_orders(date, market_conditions)
        movements.extend(po_data['movements'])
        
        # Insert purchase orders and items separately
        if po_data['purchase_orders']:
            self.insert_purchase_orders(po_data['purchase_orders'], po_data['purchase_order_items'])
        
        # Insert all data
        self.insert_daily_data(orders, order_items, movements)
    
    def generate_realistic_order(self, date: datetime, order_num: int, market_conditions: Dict) -> Dict:
        """Generate a realistic B2B tech order"""
        
        # Order characteristics
        order_id = str(uuid.uuid4())
        fulfillment_location = random.choice([loc for loc in self.locations if loc.type == 'warehouse'])
        
        # Customer type affects order patterns
        customer_types = ['enterprise', 'smb', 'government', 'education', 'reseller']
        customer_type = random.choices(customer_types, weights=[25, 35, 15, 15, 10])[0]
        
        # Order timing during business hours
        hour = random.choices(range(8, 18), weights=[5,8,12,15,18,20,18,15,12,8])[0]
        order_time = date.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))
        
        # Product selection based on customer type
        if customer_type == 'enterprise':
            # Larger orders, premium products, servers/networking focus
            categories = random.choices(['Laptops', 'Monitors', 'Networking', 'Servers', 'Software'], 
                                      weights=[20, 15, 30, 25, 10])
            num_line_items = random.choices([1, 2, 3, 4, 5], weights=[10, 20, 30, 25, 15])[0]
        elif customer_type == 'smb':
            # Mixed orders, practical focus
            categories = random.choices(['Laptops', 'Monitors', 'Desktops', 'Accessories', 'Software'], 
                                      weights=[25, 20, 20, 25, 10])
            num_line_items = random.choices([1, 2, 3, 4], weights=[20, 35, 30, 15])[0]
        elif customer_type == 'education':
            # Budget focus, bulk accessories, some laptops
            categories = random.choices(['Laptops', 'Monitors', 'Accessories', 'Software'], 
                                      weights=[30, 25, 35, 10])
            num_line_items = random.choices([2, 3, 4, 5], weights=[20, 30, 35, 15])[0]
        else:  # government/reseller
            categories = random.choices(['Laptops', 'Desktops', 'Monitors', 'Storage'], 
                                      weights=[25, 25, 25, 25])
            num_line_items = random.choices([1, 2, 3], weights=[30, 40, 30])[0]
        
        # Select products for this order
        available_products = [p for p in self.products if p.category in categories[:num_line_items]]
        if not available_products:
            return None
        
        selected_products = random.sample(available_products, min(num_line_items, len(available_products)))
        
        order_total = Decimal('0.00')
        items = []
        movements = []
        
        for product in selected_products:
            # Calculate demand with all factors
            seasonal_mult = self.get_seasonal_multiplier(date, product.category)
            covid_impact = product.covid_impact_factor if date < self.normalization_start else 1.0
            
            adjusted_velocity = (product.base_velocity * seasonal_mult * 
                               market_conditions['demand_multiplier'] * covid_impact)
            
            # Quantity based on customer type and product
            if customer_type == 'enterprise' and product.category in ['Servers', 'Networking']:
                base_qty = max(1, int(adjusted_velocity * 0.3))  # Lower qty for high-value items
            elif customer_type == 'education' and product.category == 'Accessories':
                base_qty = max(1, int(adjusted_velocity * 2.0))  # Bulk purchases
            else:
                base_qty = max(1, int(adjusted_velocity))
            
            quantity = poisson_approx(base_qty)
            quantity = max(1, min(quantity, 50))  # Reasonable limits
            
            # Pricing with market inflation
            unit_price = Decimal(str(product.price * market_conditions['price_inflation'] * random.uniform(0.95, 1.02)))
            line_total = unit_price * quantity
            order_total += line_total
            
            # Create order item
            items.append((
                str(uuid.uuid4()),
                order_id,
                product.id,
                quantity,
                unit_price
            ))
            
            # Create inventory movement
            movements.append((
                str(uuid.uuid4()),
                product.id,
                fulfillment_location.id,
                -quantity,
                'out',
                order_time,
                f'B2B Sale - {customer_type.title()} Customer'
            ))
        
        # Generate order number
        order_date_str = order_time.strftime("%Y%m%d")
        order_number = f"TF-{order_date_str}-{order_num:04d}"
        
        # Fulfillment timing based on order complexity and market conditions
        fulfillment_delay_hours = random.uniform(2, 24) / market_conditions['supply_reliability']
        fulfilled_at = order_time + timedelta(hours=fulfillment_delay_hours)
        
        order = (
            order_id,
            self.techflow_org_id,
            order_number,
            'b2b_portal',
            'completed',
            order_time,
            fulfilled_at,
            fulfillment_location.id,
            order_total
        )
        
        return {
            'order': order,
            'items': items,
            'movements': movements
        }
    
    def generate_purchase_orders(self, date: datetime, market_conditions: Dict) -> Dict:
        """Generate realistic purchase orders and associated inventory movements"""
        purchase_orders = []
        purchase_order_items = []
        movements = []
        
        # PO generation probability affected by market conditions and day of week
        base_po_prob = 0.08  # 8% chance of creating a PO per day
        supply_adjusted_prob = base_po_prob * market_conditions['supply_reliability']
        
        # More POs on weekdays
        if date.weekday() < 5:
            daily_prob = supply_adjusted_prob
        else:
            daily_prob = supply_adjusted_prob * 0.2
        
        # Skip PO generation randomly
        if random.random() > daily_prob:
            return {'purchase_orders': [], 'purchase_order_items': [], 'movements': []}
        
        # Get suppliers from database
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, lead_time_days, minimum_order_quantity FROM suppliers WHERE org_id = %s", 
                       (self.techflow_org_id,))
            suppliers = cur.fetchall()
        
        if not suppliers:
            return {'purchase_orders': [], 'purchase_order_items': [], 'movements': []}
        
        # Select supplier and products to restock
        supplier = random.choice(suppliers)
        
        # Select products that might need restocking (simplified logic)
        products_to_restock = []
        for product in self.products:
            restock_prob = 0.15  # 15% chance per product
            if product.category in ['Servers', 'Networking']:
                restock_prob = 0.08  # Lower for expensive items
            elif product.category in ['Accessories', 'Storage']:
                restock_prob = 0.25  # Higher for fast movers
            
            if random.random() < restock_prob:
                products_to_restock.append(product)
        
        if not products_to_restock:
            return {'purchase_orders': [], 'purchase_order_items': [], 'movements': []}
        
        # Create purchase order
        po_id = str(uuid.uuid4())
        po_date = date.replace(hour=random.randint(8, 17), minute=random.randint(0, 59))
        po_number = f"PO-{po_date.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        expected_delivery = po_date + timedelta(days=supplier['lead_time_days'] + random.randint(-2, 3))
        
        po_total = Decimal('0.00')
        
        # Create PO items
        for product in products_to_restock:
            # Determine order quantity
            if product.category in ['Servers', 'Networking']:
                base_qty = random.randint(1, max(1, product.reorder_point // 2))
            elif product.category in ['Accessories', 'Storage']:
                base_qty = random.randint(product.reorder_point, product.reorder_point * 2)
            else:
                base_qty = random.randint(product.reorder_point // 2, product.reorder_point)
            
            # Apply supplier MOQ
            quantity = max(supplier['minimum_order_quantity'], base_qty)
            
            # Adjust for supply chain conditions
            if random.random() < product.supply_chain_risk * (1 - market_conditions['supply_reliability']):
                quantity = max(1, int(quantity * 0.6))  # Reduced availability
            
            unit_cost = Decimal(str(product.cost * random.uniform(0.95, 1.05)))  # Cost variance
            total_cost = unit_cost * quantity
            po_total += total_cost
            
            # Create PO item
            purchase_order_items.append((
                str(uuid.uuid4()),
                po_id,
                product.id,
                quantity,
                unit_cost,
                total_cost,
                quantity  # received_quantity (assume full delivery for now)
            ))
            
            # Create corresponding inventory movement (delivery)
            delivery_date = expected_delivery + timedelta(
                hours=random.randint(8, 16),
                minutes=random.randint(0, 59)
            )
            
            main_warehouse = next((loc for loc in self.locations if 'Main' in loc.name), self.locations[0])
            
            movements.append((
                str(uuid.uuid4()),
                product.id,
                main_warehouse.id,
                quantity,
                'in',
                delivery_date,
                f'PO Receipt - {po_number} from {supplier["name"]}'
            ))
        
        # Create purchase order record
        purchase_orders.append((
            po_id,
            self.techflow_org_id,
            supplier['id'],
            po_number,
            'received',  # status
            po_date,
            expected_delivery,
            expected_delivery,  # received_date (same as expected for simplicity)
            po_total,
            f'Bulk restock order from {supplier["name"]}'
        ))
        
        return {
            'purchase_orders': purchase_orders,
            'purchase_order_items': purchase_order_items,
            'movements': movements
        }
    
    def insert_purchase_orders(self, purchase_orders: List, purchase_order_items: List):
        """Insert purchase order data"""
        with self.conn.cursor() as cur:
            if purchase_orders:
                execute_values(cur, """
                    INSERT INTO purchase_orders 
                    (id, org_id, supplier_id, po_number, status, order_date, expected_date, received_date, total_amount, notes)
                    VALUES %s
                """, purchase_orders)
            
            if purchase_order_items:
                execute_values(cur, """
                    INSERT INTO purchase_order_items 
                    (id, purchase_order_id, product_id, quantity, unit_cost, total_cost, received_quantity)
                    VALUES %s
                """, purchase_order_items)
    
    def insert_daily_data(self, orders: List, order_items: List, movements: List):
        """Insert daily data into database"""
        if not (orders or order_items or movements):
            return
            
        with self.conn.cursor() as cur:
            if orders:
                execute_values(cur, """
                    INSERT INTO orders (id, org_id, order_number, channel, status, ordered_at, fulfilled_at, location_id, total_amount)
                    VALUES %s
                """, orders)
            
            if order_items:
                execute_values(cur, """
                    INSERT INTO order_items (id, order_id, product_id, quantity, unit_price)
                    VALUES %s
                """, order_items)
            
            if movements:
                execute_values(cur, """
                    INSERT INTO inventory_movements 
                    (id, product_id, location_id, quantity, movement_type, timestamp, notes)
                    VALUES %s
                """, movements)
    
    def is_holiday(self, date: datetime) -> bool:
        """Check for major US business holidays"""
        holidays = [
            (1, 1), (7, 4), (11, 26), (11, 27), (12, 24), (12, 25), (12, 31)
        ]
        return (date.month, date.day) in holidays
    
    def generate_all_data(self):
        """Generate complete 5-year dataset"""
        print(f"Generating TechFlow Solutions data from {self.start_date.date()} to {self.end_date.date()}")
        
        self.generate_initial_inventory()
        
        current_date = self.start_date
        total_days = (self.end_date - self.start_date).days + 1
        
        for day_num in range(total_days):
            if day_num % 100 == 0:  # Progress every 100 days
                print(f"Progress: {day_num}/{total_days} days ({day_num/total_days*100:.1f}%) - {current_date.strftime('%Y-%m-%d')}")
            
            self.generate_daily_data(current_date)
            current_date += timedelta(days=1)
        
        print("Data generation complete!")
        self.print_summary()
    
    def print_summary(self):
        """Print comprehensive summary statistics"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Basic counts
            cur.execute("SELECT COUNT(*) as count FROM orders")
            order_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM order_items") 
            item_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM inventory_movements")
            movement_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM purchase_orders")
            po_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM purchase_order_items")
            po_item_count = cur.fetchone()['count']
            
            cur.execute("SELECT SUM(total_amount) as total FROM orders")
            total_revenue = cur.fetchone()['total'] or 0
            
            cur.execute("SELECT SUM(total_amount) as total FROM purchase_orders")
            total_po_spend = cur.fetchone()['total'] or 0
            
            # Yearly breakdown
            cur.execute("""
                SELECT EXTRACT(YEAR FROM ordered_at) as year,
                       COUNT(*) as orders,
                       SUM(total_amount) as revenue
                FROM orders 
                GROUP BY EXTRACT(YEAR FROM ordered_at)
                ORDER BY year
            """)
            yearly_stats = cur.fetchall()
            
            # Category breakdown
            cur.execute("""
                SELECT p.category, 
                       COUNT(oi.*) as items_sold,
                       SUM(oi.quantity * oi.unit_price) as category_revenue
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                GROUP BY p.category
                ORDER BY category_revenue DESC
            """)
            category_stats = cur.fetchall()
            
            print("\n" + "="*70)
            print("TECHFLOW SOLUTIONS - 5 YEAR DATA SUMMARY")
            print("="*70)
            print(f"Total Sales Orders: {order_count:,}")
            print(f"Total Order Items: {item_count:,}")
            print(f"Total Purchase Orders: {po_count:,}")
            print(f"Total PO Items: {po_item_count:,}")
            print(f"Total Inventory Movements: {movement_count:,}")
            print(f"Total Revenue: ${total_revenue:,.2f}")
            print(f"Total PO Spend: ${total_po_spend:,.2f}")
            print(f"Average Order Value: ${total_revenue/order_count if order_count else 0:,.2f}")
            print(f"Gross Margin: ${total_revenue - total_po_spend:,.2f} ({((total_revenue - total_po_spend)/total_revenue*100) if total_revenue else 0:.1f}%)")
            
            print(f"\nYEARLY BREAKDOWN:")
            print("-" * 40)
            for year_stat in yearly_stats:
                year = int(year_stat['year'])
                orders = year_stat['orders']
                revenue = year_stat['revenue'] or 0
                avg_order = revenue / orders if orders else 0
                print(f"{year}: {orders:,} orders, ${revenue:,.2f} revenue (${avg_order:,.2f} AOV)")
            
            print(f"\nCATEGORY PERFORMANCE:")
            print("-" * 40)
            for cat_stat in category_stats:
                category = cat_stat['category']
                items = cat_stat['items_sold']
                revenue = cat_stat['category_revenue'] or 0
                print(f"{category:<12}: {items:,} items sold, ${revenue:,.2f} revenue")
            
            print("="*70)
            print("Historical Events Modeled:")
            print("• COVID-19 remote work surge (Mar 2020 - Jun 2021)")
            print("• Supply chain shortages (Jun 2021 - Jun 2022)")
            print("• Chip shortage impact on laptops/networking")
            print("• Seasonal B2B patterns (back-to-school, fiscal years)")
            print("• Market recovery and normalization (2022-2025)")
            print("="*70)

def main():
    db_url = os.getenv("DATABASE_URL", 
                      "postgresql://stockpilot:stockpilot_dev@localhost:5432/stockpilot")
    
    print("TechFlow Solutions - 5 Year Data Generator")
    print("IT Equipment Distributor: Aug 14, 2020 - Aug 13, 2025")
    print("-" * 60)
    
    generator = TechFlowDataGenerator(db_url)
    
    try:
        generator.connect()
        generator.setup_techflow_business()
        generator.generate_all_data()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        generator.disconnect()
    
    print("\nTechFlow Solutions dataset generated successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
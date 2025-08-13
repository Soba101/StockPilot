#!/usr/bin/env python3
"""
Generate one year of realistic inventory and sales data for StockPilot
Date range: August 14, 2024 to August 13, 2025
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
from typing import List, Dict, Any
import math

# Simple Poisson approximation using normal distribution for large lambda
def poisson_approx(lam):
    """Approximate Poisson distribution for reasonable lambda values"""
    if lam <= 0:
        return 0
    elif lam < 10:
        # For small lambda, use exponential method
        L = math.exp(-lam)
        k = 0
        p = 1
        while p > L:
            k += 1
            p *= random.random()
        return k - 1
    else:
        # For larger lambda, use normal approximation
        return max(0, int(random.gauss(lam, math.sqrt(lam)) + 0.5))

# Add the app directory to Python path
sys.path.append('/Users/don/DocumentsMac/StockPilot/backend')

@dataclass
class Product:
    id: str
    org_id: str
    sku: str
    name: str
    cost: float
    price: float
    category: str
    reorder_point: int
    seasonal_factor: float = 1.0
    base_velocity: float = 2.0  # units per day base velocity

@dataclass
class Location:
    id: str
    org_id: str
    name: str
    type: str

class YearlyDataGenerator:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn = None
        self.start_date = datetime(2024, 8, 14, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 8, 13, 23, 59, 59, tzinfo=timezone.utc)
        self.products: List[Product] = []
        self.locations: List[Location] = []
        self.org_ids: List[str] = []
        
    def connect(self):
        """Connect to database"""
        self.conn = psycopg2.connect(self.db_url)
        self.conn.autocommit = True
        print("Connected to database")
        
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def load_existing_data(self):
        """Load existing organizations, locations, and products"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Load organizations
            cur.execute("SELECT id FROM organizations")
            self.org_ids = [row['id'] for row in cur.fetchall()]
            print(f"Found {len(self.org_ids)} organizations")
            
            # Load locations
            cur.execute("SELECT id, org_id, name, type FROM locations")
            for row in cur.fetchall():
                self.locations.append(Location(
                    id=str(row['id']),
                    org_id=str(row['org_id']),
                    name=row['name'],
                    type=row['type']
                ))
            print(f"Found {len(self.locations)} locations")
            
            # Load products with seasonal factors
            cur.execute("""
                SELECT id, org_id, sku, name, cost, price, category, reorder_point 
                FROM products 
                ORDER BY category, name
            """)
            
            for row in cur.fetchall():
                # Assign seasonal patterns based on category
                seasonal_factor = self.get_seasonal_factor(row['category'])
                base_velocity = self.get_base_velocity(row['category'])
                
                self.products.append(Product(
                    id=str(row['id']),
                    org_id=str(row['org_id']),
                    sku=row['sku'],
                    name=row['name'],
                    cost=float(row['cost'] or 0),
                    price=float(row['price'] or 0),
                    category=row['category'] or 'General',
                    reorder_point=row['reorder_point'] or 10,
                    seasonal_factor=seasonal_factor,
                    base_velocity=base_velocity
                ))
            print(f"Found {len(self.products)} products")
    
    def get_seasonal_factor(self, category: str) -> float:
        """Get seasonal multiplier based on category"""
        seasonal_patterns = {
            'Electronics': 1.2,      # Higher demand in back-to-school/holidays
            'Sports & Outdoors': 0.8, # Lower in winter months
            'Home & Garden': 1.1,    # Moderate seasonal variation
            'Office': 0.9,           # Slight back-to-school bump
            'Networking': 1.0,       # Stable B2B demand
        }
        return seasonal_patterns.get(category, 1.0)
    
    def get_base_velocity(self, category: str) -> float:
        """Get base daily velocity by category"""
        velocity_patterns = {
            'Electronics': 3.5,
            'Sports & Outdoors': 2.2,
            'Home & Garden': 2.8,
            'Office': 4.2,
            'Networking': 1.5,  # Lower volume B2B
        }
        return velocity_patterns.get(category, 2.5)
    
    def get_seasonal_multiplier(self, date: datetime, category: str) -> float:
        """Calculate seasonal demand multiplier for a specific date"""
        day_of_year = date.timetuple().tm_yday
        
        # Different seasonal patterns by category
        if category == 'Sports & Outdoors':
            # Peak in spring/summer, low in winter
            return 0.7 + 0.6 * math.sin((day_of_year - 80) * 2 * math.pi / 365)
        elif category == 'Electronics':
            # Peaks in back-to-school (Aug) and holidays (Nov-Dec)
            base = 1.0
            if 220 <= day_of_year <= 250:  # August back-to-school
                base += 0.4
            elif 315 <= day_of_year <= 365:  # Holiday season
                base += 0.6
            return base
        elif category == 'Home & Garden':
            # Peak in spring, moderate in summer/fall
            return 0.8 + 0.4 * math.sin((day_of_year - 60) * 2 * math.pi / 365)
        else:
            # Stable demand with slight holiday bump
            base = 1.0
            if 315 <= day_of_year <= 365:
                base += 0.2
            return base
    
    def clear_existing_data(self):
        """Clear existing orders and inventory movements for clean slate"""
        print("Clearing existing transactional data...")
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM order_items")
            cur.execute("DELETE FROM orders") 
            cur.execute("DELETE FROM inventory_movements")
        print("Cleared existing data")
    
    def generate_initial_inventory(self):
        """Generate initial inventory levels for all products"""
        print("Generating initial inventory...")
        
        movements = []
        current_date = self.start_date
        
        for product in self.products:
            # Get a suitable warehouse location for this product's org
            warehouses = [loc for loc in self.locations 
                         if loc.org_id == product.org_id and loc.type == 'warehouse']
            if not warehouses:
                continue
                
            warehouse = random.choice(warehouses)
            
            # Initial stock: 2-4x reorder point + some randomness
            initial_stock = random.randint(
                product.reorder_point * 2,
                product.reorder_point * 4 + 50
            )
            
            movements.append((
                str(uuid.uuid4()),
                product.id,
                warehouse.id,
                initial_stock,
                'in',
                current_date,
                'Initial inventory setup'
            ))
        
        # Insert all initial movements
        with self.conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO inventory_movements 
                (id, product_id, location_id, quantity, movement_type, timestamp, notes)
                VALUES %s
            """, movements)
        
        print(f"Generated initial inventory for {len(movements)} products")
    
    def generate_daily_data(self, date: datetime):
        """Generate realistic daily sales and inventory movements"""
        movements = []
        orders = []
        order_items = []
        
        # Skip weekends for B2B orders (but include some weekend consumer sales)
        is_weekend = date.weekday() >= 5
        is_holiday = self.is_holiday(date)
        
        for org_id in self.org_ids:
            org_products = [p for p in self.products if p.org_id == org_id]
            org_locations = [l for l in self.locations if l.org_id == org_id]
            
            if not org_products or not org_locations:
                continue
            
            # Determine order patterns based on org type (inferred from products)
            is_b2b_org = any('Networking' in p.category for p in org_products)
            
            # Skip B2B orders on weekends/holidays
            if is_b2b_org and (is_weekend or is_holiday):
                continue
            
            # Generate orders for this org
            daily_orders = self.generate_org_daily_orders(
                date, org_id, org_products, org_locations, is_b2b_org
            )
            
            orders.extend(daily_orders['orders'])
            order_items.extend(daily_orders['order_items'])
            movements.extend(daily_orders['movements'])
            
            # Generate restocking/receiving
            restock_movements = self.generate_restocking(
                date, org_id, org_products, org_locations
            )
            movements.extend(restock_movements)
        
        # Insert into database
        self.insert_daily_data(orders, order_items, movements)
    
    def generate_org_daily_orders(self, date: datetime, org_id: str, 
                                  products: List[Product], locations: List[Location],
                                  is_b2b: bool) -> Dict[str, List]:
        """Generate orders for a specific organization"""
        orders = []
        order_items = []
        movements = []
        
        # Determine number of orders for the day
        if is_b2b:
            # B2B: Fewer, larger orders
            num_orders = random.choices([0, 1, 2, 3], weights=[20, 40, 30, 10])[0]
        else:
            # B2C: More frequent, smaller orders
            base_orders = 5
            # Weekend boost for consumer retail
            if date.weekday() >= 5:
                base_orders = 8
            num_orders = poisson_approx(base_orders)
        
        for _ in range(num_orders):
            order_id = str(uuid.uuid4())
            
            # Select fulfillment location
            fulfillment_locations = [l for l in locations if l.type in ['warehouse', 'store']]
            if not fulfillment_locations:
                continue
            fulfillment_location = random.choice(fulfillment_locations)
            
            # Order timestamp (spread throughout business hours)
            if is_b2b:
                hour = random.randint(8, 17)  # Business hours
            else:
                hour = random.randint(6, 22)  # Extended hours
            
            order_time = date.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Select products for this order
            if is_b2b:
                # B2B: Fewer product types, higher quantities
                num_items = random.choices([1, 2, 3, 4], weights=[30, 35, 25, 10])[0]
            else:
                # B2C: More varied product selection
                num_items = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
            
            selected_products = random.sample(products, min(num_items, len(products)))
            
            order_total = Decimal('0.00')
            
            for product in selected_products:
                # Calculate demand with seasonal factors
                seasonal_mult = self.get_seasonal_multiplier(date, product.category)
                adjusted_velocity = product.base_velocity * product.seasonal_factor * seasonal_mult
                
                # Determine quantity (Poisson distribution around adjusted velocity)
                if is_b2b:
                    # B2B orders typically larger
                    base_qty = max(1, int(adjusted_velocity * random.uniform(0.5, 2.0)))
                    quantity = poisson_approx(base_qty * 2)  # Larger B2B orders
                else:
                    # B2C orders typically smaller
                    quantity = poisson_approx(max(1, adjusted_velocity))
                
                quantity = max(1, quantity)  # Ensure at least 1
                
                # Use current price with some variance
                unit_price = Decimal(str(product.price * random.uniform(0.95, 1.05)))
                line_total = unit_price * quantity
                order_total += line_total
                
                # Create order item
                order_items.append((
                    str(uuid.uuid4()),
                    order_id,
                    product.id,
                    quantity,
                    unit_price
                ))
                
                # Create inventory movement (out)
                movements.append((
                    str(uuid.uuid4()),
                    product.id,
                    fulfillment_location.id,
                    -quantity,  # Negative for outbound
                    'out',
                    order_time,
                    f'Sale - Order {order_id[:8]}'
                ))
            
            # Generate order number (format: ORD-YYYYMMDD-#### for the day)
            order_date_str = order_time.strftime("%Y%m%d")
            order_counter = len(orders) + 1  # Simple counter for the day
            order_number = f"ORD-{order_date_str}-{order_counter:04d}"
            
            # Create order record
            orders.append((
                order_id,
                org_id,
                order_number,
                'online' if not is_b2b else 'portal',  # channel
                'completed',
                order_time,
                order_time + timedelta(minutes=random.randint(30, 120)),  # fulfilled_at
                fulfillment_location.id,  # location_id
                order_total
            ))
        
        return {
            'orders': orders,
            'order_items': order_items,
            'movements': movements
        }
    
    def generate_restocking(self, date: datetime, org_id: str,
                           products: List[Product], locations: List[Location]) -> List:
        """Generate restocking/receiving movements"""
        movements = []
        
        # Get warehouse locations
        warehouses = [l for l in locations if l.type == 'warehouse']
        if not warehouses:
            return movements
        
        # Restock some products randomly (simulate deliveries)
        # Higher chance on weekdays
        restock_probability = 0.15 if date.weekday() < 5 else 0.05
        
        for product in products:
            if random.random() < restock_probability:
                warehouse = random.choice(warehouses)
                
                # Restock quantity based on reorder point and category
                if 'Networking' in product.category:
                    # B2B products: smaller, less frequent restocks
                    quantity = random.randint(
                        product.reorder_point // 2,
                        product.reorder_point * 2
                    )
                else:
                    # Consumer products: larger restocks
                    quantity = random.randint(
                        product.reorder_point,
                        product.reorder_point * 3
                    )
                
                # Random time during business hours
                restock_time = date.replace(
                    hour=random.randint(8, 16),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                movements.append((
                    str(uuid.uuid4()),
                    product.id,
                    warehouse.id,
                    quantity,
                    'in',
                    restock_time,
                    'Purchase order receipt'
                ))
        
        return movements
    
    def insert_daily_data(self, orders: List, order_items: List, movements: List):
        """Insert all daily data into database"""
        if not (orders or order_items or movements):
            return
        
        with self.conn.cursor() as cur:
            # Insert orders
            if orders:
                execute_values(cur, """
                    INSERT INTO orders (id, org_id, order_number, channel, status, ordered_at, fulfilled_at, location_id, total_amount)
                    VALUES %s
                """, orders)
            
            # Insert order items
            if order_items:
                execute_values(cur, """
                    INSERT INTO order_items (id, order_id, product_id, quantity, unit_price)
                    VALUES %s
                """, order_items)
            
            # Insert inventory movements
            if movements:
                execute_values(cur, """
                    INSERT INTO inventory_movements 
                    (id, product_id, location_id, quantity, movement_type, timestamp, notes)
                    VALUES %s
                """, movements)
    
    def is_holiday(self, date: datetime) -> bool:
        """Check if date is a major holiday (simplified)"""
        # Major US holidays that might affect business
        holidays = [
            (1, 1),   # New Year's Day
            (7, 4),   # Independence Day  
            (11, 26), # Thanksgiving (approximate)
            (12, 25), # Christmas
        ]
        return (date.month, date.day) in holidays
    
    def generate_all_data(self):
        """Generate complete yearly dataset"""
        print(f"Generating data from {self.start_date.date()} to {self.end_date.date()}")
        
        # Generate initial inventory
        self.generate_initial_inventory()
        
        # Generate daily data
        current_date = self.start_date
        total_days = (self.end_date - self.start_date).days + 1
        
        for day_num in range(total_days):
            if day_num % 30 == 0:  # Progress every 30 days
                print(f"Progress: {day_num}/{total_days} days ({day_num/total_days*100:.1f}%)")
            
            self.generate_daily_data(current_date)
            current_date += timedelta(days=1)
        
        print("Data generation complete!")
        
        # Print summary statistics
        self.print_summary()
    
    def print_summary(self):
        """Print summary statistics"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM orders")
            order_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM order_items")
            item_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM inventory_movements")
            movement_count = cur.fetchone()[0]
            
            cur.execute("SELECT SUM(total_amount) FROM orders")
            total_revenue = cur.fetchone()[0] or 0
            
            print("\n" + "="*50)
            print("DATA GENERATION SUMMARY")
            print("="*50)
            print(f"Orders generated: {order_count:,}")
            print(f"Order items: {item_count:,}")
            print(f"Inventory movements: {movement_count:,}")
            print(f"Total revenue: ${total_revenue:,.2f}")
            print(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
            print("="*50)

def main():
    # Database connection string
    db_url = os.getenv("DATABASE_URL", 
                       "postgresql://stockpilot:stockpilot_dev@localhost:5432/stockpilot")
    
    print("StockPilot Yearly Data Generator")
    print("Generating 1 year of data ending August 13, 2025")
    print("-" * 50)
    
    generator = YearlyDataGenerator(db_url)
    
    try:
        generator.connect()
        generator.load_existing_data()
        generator.clear_existing_data()
        generator.generate_all_data()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        generator.disconnect()
    
    print("\nData generation completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
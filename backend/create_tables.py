#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.dirname(__file__))

from app.core.database import engine, Base
from app.models.organization import Organization
from app.models.location import Location
from app.models.product import Product  
from app.models.inventory import InventoryMovement

def create_tables():
    """Create all tables in the database."""
    print("Creating database tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # List created tables
        inspector = engine.inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    create_tables()
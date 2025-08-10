#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.organization import Organization

def test_db_connection():
    """Test database connection and query."""
    print("Testing database connection...")
    
    try:
        db = SessionLocal()
        
        # Try to query organizations
        orgs = db.query(Organization).all()
        print(f"✅ Found {len(orgs)} organizations")
        
        for org in orgs:
            print(f"   - {org.name} (ID: {org.id})")
            
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    test_db_connection()
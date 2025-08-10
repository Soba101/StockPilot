#!/usr/bin/env python3

import psycopg2

def test_from_container():
    """Test connection from inside container context."""
    print("Testing connection from container perspective...")
    
    try:
        # Try connecting to localhost from container's perspective
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="stockpilot",
            password="stockpilot_dev",
            database="stockpilot"
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Connected! PostgreSQL version: {version[0]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    test_from_container()
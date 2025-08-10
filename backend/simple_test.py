#!/usr/bin/env python3

import psycopg2

def test_simple_connection():
    """Test simple database connection with psycopg2."""
    print("Testing simple connection...")
    
    try:
        # Try with password
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="stockpilot",
            password="stockpilot_dev",
            database="stockpilot"
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Connected! PostgreSQL version: {version[0]}")
        
        cur.execute("SELECT * FROM organizations LIMIT 1;")
        org = cur.fetchone()
        print(f"✅ Sample organization: {org}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    test_simple_connection()
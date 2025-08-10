#!/usr/bin/env python3

import psycopg2

def test_postgres_db():
    """Test connecting to postgres database instead of stockpilot."""
    print("🔍 Testing connection to 'postgres' database:")
    try:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="stockpilot",
            password="stockpilot_dev",
            database="postgres"  # Connect to postgres db instead
        )
        
        cur = conn.cursor()
        cur.execute("SELECT current_user, current_database();")
        result = cur.fetchone()
        print(f"✅ Success! User: {result[0]}, Database: {result[1]}")
        
        # List all databases
        cur.execute("SELECT datname FROM pg_database;")
        databases = cur.fetchall()
        print(f"📋 Available databases: {[db[0] for db in databases]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    test_postgres_db()
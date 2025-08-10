#!/usr/bin/env python3

import psycopg2

def test_postgres_user():
    """Test connection with postgres user."""
    print("🔍 Testing connection with postgres user:")
    try:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="postgres",
            password="stockpilot_dev",
            database="stockpilot"
        )
        
        cur = conn.cursor()
        cur.execute("SELECT current_user, version();")
        result = cur.fetchone()
        print(f"✅ Success! User: {result[0]}")
        print(f"✅ PostgreSQL: {result[1][:50]}...")
        
        # Test if our tables exist
        cur.execute("SELECT COUNT(*) FROM organizations;")
        count = cur.fetchone()[0]
        print(f"✅ Found {count} organizations")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    test_postgres_user()
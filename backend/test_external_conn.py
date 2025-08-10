#!/usr/bin/env python3
import psycopg2
import os

def test_connection_debug():
    """Debug external PostgreSQL connection."""
    
    print("🔍 Testing external connection to PostgreSQL...")
    
    # Test basic connection
    try:
        print("Attempting to connect with postgres user...")
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
        
        cur.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ OperationalError: {e}")
        
        # Try connecting to the default postgres database first
        try:
            print("Trying to connect to default 'postgres' database...")
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                user="postgres",
                password="stockpilot_dev",
                database="postgres"
            )
            
            cur = conn.cursor()
            cur.execute("SELECT current_user;")
            result = cur.fetchone()
            print(f"✅ Connected to postgres db as: {result[0]}")
            
            # List all databases
            cur.execute("SELECT datname FROM pg_database;")
            dbs = cur.fetchall()
            print(f"Available databases: {[db[0] for db in dbs]}")
            
            cur.close()
            conn.close()
            
            # Now try connecting to stockpilot database
            print("Now trying stockpilot database...")
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                user="postgres",
                password="stockpilot_dev",
                database="stockpilot"
            )
            
            cur = conn.cursor()
            cur.execute("SELECT current_user;")
            result = cur.fetchone()
            print(f"✅ Connected to stockpilot db as: {result[0]}")
            
            cur.close()
            conn.close()
            return True
            
        except psycopg2.OperationalError as e2:
            print(f"❌ Still failed: {e2}")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_connection_debug()
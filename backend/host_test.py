#!/usr/bin/env python3

import psycopg2

def test_different_hosts():
    """Test connection with different host values."""
    hosts_to_try = [
        ("127.0.0.1", "IPv4 loopback"),
        ("localhost", "localhost resolution"),
        ("0.0.0.0", "All interfaces"),
    ]
    
    for host, description in hosts_to_try:
        print(f"\n🔍 Testing {description} ({host}):")
        try:
            conn = psycopg2.connect(
                host=host,
                port=5432,
                user="stockpilot",
                password="stockpilot_dev",
                database="stockpilot"
            )
            
            cur = conn.cursor()
            cur.execute("SELECT current_user;")
            user = cur.fetchone()
            print(f"✅ Success! Connected as: {user[0]}")
            
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return False

if __name__ == "__main__":
    test_different_hosts()
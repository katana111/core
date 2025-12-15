"""
Example: Initialize and test centralized database connection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import get_db, DatabaseConfig

def main():
    print("="*60)
    print("DATABASE CONNECTION TEST")
    print("="*60)
    
    # Method 1: Initialize with environment variables (default)
    print("\n1. Initializing with default configuration...")
    db = get_db()
    db.initialize()
    
    # Test connection
    if db.test_connection():
        print("✅ Connection successful!")
        
        # Show config
        config = db.config
        print(f"\nConnected to:")
        print(f"  Host: {config.host}:{config.port}")
        print(f"  Database: {config.database}")
        print(f"  User: {config.username}")
    else:
        print("❌ Connection failed!")
        return
    
    # Method 2: Query example
    print("\n" + "="*60)
    print("QUERY EXAMPLE")
    print("="*60)
    
    try:
        with db.get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM competitors")
            result = cursor.fetchone()
            print(f"\nTotal competitors in database: {result['count']}")
            
            # Get recent competitors
            cursor.execute("SELECT name, website, founded_year FROM competitors ORDER BY updated_at DESC LIMIT 5")
            recent = cursor.fetchall()
            
            print("\nRecent competitors:")
            for comp in recent:
                print(f"  - {comp['name']} ({comp['website']}) - Founded: {comp['founded_year']}")
    
    except Exception as e:
        print(f"❌ Query failed: {e}")
    
    # Method 3: Custom configuration example
    print("\n" + "="*60)
    print("CUSTOM CONFIGURATION EXAMPLE")
    print("="*60)
    
    custom_config = DatabaseConfig(
        host="127.0.0.1",
        port=3306,
        database="insider",
        username="root",
        password="password"
    )
    
    print(f"Custom config created:")
    print(f"  Database: {custom_config.database}")
    print(f"  Charset: {custom_config.charset}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()

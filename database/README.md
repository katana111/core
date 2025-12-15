# Database Package - Centralized Database Management

## Overview

Centralized database configuration and connection management for all InsiderAI services using dependency injection pattern.

## Architecture

```
database/
├── __init__.py          # Package exports
├── config.py            # Configuration management (from env or dict)
├── connection.py        # Connection pooling & singleton pattern
└── utils.py             # Helper functions for common operations
```

## Features

✅ **Singleton Pattern** - Single shared database connection across all services  
✅ **Connection Pooling** - Efficient connection reuse (pool size: 5)  
✅ **Dependency Injection** - Services get DB via `get_db()`  
✅ **Environment Configuration** - Loads from `.env` file  
✅ **Context Managers** - Auto-commit/rollback transactions  
✅ **Thread-Safe** - Multiple services can use concurrently  

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=insider
DB_USERNAME=root
DB_PASSWORD=password
```

### Programmatic Configuration

```python
from database import DatabaseConfig, set_db_config

# Create custom config
config = DatabaseConfig(
    host="localhost",
    port=3306,
    database="mydb",
    username="user",
    password="pass"
)

# Set globally
set_db_config(config)
```

## Usage

### Basic Setup

```python
from database import get_db

# Get database instance (singleton)
db = get_db()

# Initialize with env config
db.initialize()

# Or initialize with custom config
from database import DatabaseConfig
config = DatabaseConfig.from_env()
db.initialize(config)
```

### Using Context Managers

#### Simple Query

```python
from database import get_db

db = get_db()

# Auto-commit on success, rollback on error
with db.get_cursor() as cursor:
    cursor.execute("SELECT * FROM competitors WHERE id = %s", (1,))
    result = cursor.fetchone()
```

#### Dictionary Results

```python
with db.get_cursor(dictionary=True) as cursor:
    cursor.execute("SELECT * FROM competitors")
    rows = cursor.fetchall()
    # rows = [{'id': 1, 'name': 'SEON', ...}, ...]
```

#### Transaction

```python
with db.transaction() as connection:
    cursor = connection.cursor()
    cursor.execute("INSERT INTO competitors ...")
    cursor.execute("UPDATE competitors ...")
    # Auto-commits on success, rolls back on error
```

### Utility Functions

```python
from database.utils import (
    execute_query,
    execute_insert,
    execute_update,
    execute_delete,
    bulk_insert
)

# Simple SELECT
results = execute_query("SELECT * FROM competitors WHERE score > %s", (50,))

# Get single row
row = execute_query("SELECT * FROM competitors WHERE id = %s", (1,), fetch_one=True)

# INSERT
competitor_id = execute_insert(
    "INSERT INTO competitors (name, website) VALUES (%s, %s)",
    ("SEON", "seon.io")
)

# UPDATE
affected = execute_update(
    "UPDATE competitors SET score = %s WHERE id = %s",
    (100, 1)
)

# DELETE
deleted = execute_delete("DELETE FROM competitors WHERE score < %s", (10,))

# Bulk insert
records = [
    {'name': 'Company1', 'website': 'site1.com'},
    {'name': 'Company2', 'website': 'site2.com'},
]
count = bulk_insert('competitors', records, on_duplicate='website=VALUES(website)')
```

## Service Integration

### Example: Tracxn Service

```python
# services/tracxn/db_operations.py
from database import get_db

class CompetitorDB:
    def __init__(self):
        self.db = get_db()  # Dependency injection
    
    def insert_competitor(self, data):
        with self.db.get_cursor() as cursor:
            query = "INSERT INTO competitors (...) VALUES (...)"
            cursor.execute(query, values)
            return cursor.lastrowid
```

### Example: New Service

```python
# services/myservice/operations.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from database import get_db

class MyDataOperations:
    def __init__(self):
        self.db = get_db()  # Reuses same connection pool
    
    def fetch_data(self):
        with self.db.get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM mytable")
            return cursor.fetchall()
```

## Connection Pool

- **Pool Size**: 5 connections
- **Auto-reconnect**: Yes
- **Session Reset**: Yes (clears variables between uses)
- **Thread-Safe**: Yes

## Best Practices

1. **Always use context managers** - Ensures proper cleanup
2. **Don't store connections** - Get from pool when needed
3. **Use parameterized queries** - Prevents SQL injection
4. **Initialize once** - Call `db.initialize()` at app startup
5. **Environment config** - Store credentials in `.env`, not code

## Testing Connection

```python
from database import get_db

db = get_db()
db.initialize()

if db.test_connection():
    print("✅ Database connected!")
else:
    print("❌ Connection failed")
```

## Migration from Old Code

### Before (Service-Specific DB)

```python
from db_config import DatabaseConfig

db_config = DatabaseConfig(
    host="127.0.0.1",
    database="insider",
    username="root",
    password="password"
)
db_config.connect()
connection = db_config.get_connection()
cursor = connection.cursor()
# ... manual cleanup
```

### After (Centralized DB)

```python
from database import get_db

db = get_db()
db.initialize()  # Once at startup

# In your code
with db.get_cursor() as cursor:
    # ... auto cleanup
```

## File Structure

```
/Users/katerynahunko/insiderai/core/
├── database/                    # Centralized DB package
│   ├── __init__.py
│   ├── config.py               # Configuration
│   ├── connection.py           # Connection pooling
│   └── utils.py                # Helper functions
├── services/
│   └── tracxn/
│       ├── db_operations.py    # Uses get_db()
│       └── scraper.py          # Uses get_db()
└── .env                        # DB credentials
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | 127.0.0.1 | MySQL server host |
| `DB_PORT` | 3306 | MySQL server port |
| `DB_DATABASE` | insider | Database name |
| `DB_USERNAME` | root | Database user |
| `DB_PASSWORD` | password | Database password |

## Error Handling

```python
from mysql.connector import Error
from database import get_db

db = get_db()

try:
    with db.get_cursor() as cursor:
        cursor.execute("SELECT * FROM competitors")
        results = cursor.fetchall()
except Error as e:
    print(f"Database error: {e}")
    # Transaction automatically rolled back
```

## Advantages

1. **Single Source of Truth** - All services use same DB config
2. **Connection Reuse** - Efficient connection pooling
3. **Consistent Error Handling** - Centralized rollback logic
4. **Easy Testing** - Mock `get_db()` for unit tests
5. **Scalable** - Add new services without duplicating DB code

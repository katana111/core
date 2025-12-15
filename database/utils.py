"""
Database utility functions and helpers
"""

from typing import Dict, List, Optional, Any
from .connection import get_db


def execute_query(query: str, params: tuple = None, fetch_one: bool = False) -> Optional[Any]:
    """
    Execute a SELECT query and return results
    
    Args:
        query: SQL query string
        params: Query parameters tuple
        fetch_one: Return single row instead of all rows
        
    Returns:
        Query results
    """
    db = get_db()
    
    with db.get_cursor(dictionary=True) as cursor:
        cursor.execute(query, params or ())
        
        if fetch_one:
            return cursor.fetchone()
        else:
            return cursor.fetchall()


def execute_insert(query: str, params: tuple) -> Optional[int]:
    """
    Execute an INSERT query and return the inserted ID
    
    Args:
        query: SQL INSERT query
        params: Query parameters tuple
        
    Returns:
        Last inserted row ID or None
    """
    db = get_db()
    
    with db.get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.lastrowid


def execute_update(query: str, params: tuple) -> int:
    """
    Execute an UPDATE query and return affected rows
    
    Args:
        query: SQL UPDATE query
        params: Query parameters tuple
        
    Returns:
        Number of affected rows
    """
    db = get_db()
    
    with db.get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.rowcount


def execute_delete(query: str, params: tuple) -> int:
    """
    Execute a DELETE query and return affected rows
    
    Args:
        query: SQL DELETE query
        params: Query parameters tuple
        
    Returns:
        Number of deleted rows
    """
    db = get_db()
    
    with db.get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.rowcount


def bulk_insert(table: str, records: List[Dict], on_duplicate: str = None) -> int:
    """
    Bulk insert records into a table
    
    Args:
        table: Table name
        records: List of dictionaries with column: value pairs
        on_duplicate: Optional ON DUPLICATE KEY UPDATE clause
        
    Returns:
        Number of inserted rows
    """
    if not records:
        return 0
    
    # Get columns from first record
    columns = list(records[0].keys())
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    
    query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
    
    if on_duplicate:
        query += f" ON DUPLICATE KEY UPDATE {on_duplicate}"
    
    db = get_db()
    
    with db.get_cursor() as cursor:
        # Prepare values
        values = [tuple(record[col] for col in columns) for record in records]
        cursor.executemany(query, values)
        return cursor.rowcount

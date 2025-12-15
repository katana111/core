"""
Database connection manager with connection pooling and dependency injection
"""

import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional
from contextlib import contextmanager

from .config import DatabaseConfig, get_db_config


class DatabaseConnection:
    """
    Database connection manager with connection pooling
    Singleton pattern for shared database access across services
    """
    
    _instance: Optional['DatabaseConnection'] = None
    _connection_pool: Optional[pooling.MySQLConnectionPool] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection manager"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._config: Optional[DatabaseConfig] = None
    
    def initialize(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database connection pool
        
        Args:
            config: DatabaseConfig instance (uses environment config if None)
        """
        if config is None:
            config = get_db_config()
        
        self._config = config
        
        try:
            self._connection_pool = pooling.MySQLConnectionPool(
                pool_name="insiderai_pool",
                pool_size=5,
                pool_reset_session=True,
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.username,
                password=config.password,
                charset=config.charset,
                collation=config.collation
            )
            print(f"✅ Database connection pool initialized for '{config.database}'")
        except Error as e:
            print(f"❌ Error initializing connection pool: {e}")
            raise
    
    def get_connection(self):
        """
        Get a connection from the pool
        
        Returns:
            MySQL connection object
        """
        if self._connection_pool is None:
            self.initialize()
        
        try:
            return self._connection_pool.get_connection()
        except Error as e:
            print(f"❌ Error getting connection from pool: {e}")
            raise
    
    @contextmanager
    def get_cursor(self, dictionary=False):
        """
        Context manager for database cursor with automatic cleanup
        
        Args:
            dictionary: Return rows as dictionaries
            
        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        """
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=dictionary)
        
        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions
        
        Usage:
            with db.transaction() as connection:
                cursor = connection.cursor()
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # Auto-commits on success, rolls back on error
        """
        connection = self.get_connection()
        
        try:
            yield connection
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
    
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Error as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def close_pool(self):
        """Close all connections in the pool"""
        if self._connection_pool:
            # Note: mysql-connector-python doesn't provide explicit pool close
            # Connections will be closed when program exits
            self._connection_pool = None
            print("✅ Connection pool closed")
    
    @property
    def config(self) -> Optional[DatabaseConfig]:
        """Get current database configuration"""
        return self._config


# Singleton instance getter
def get_db() -> DatabaseConnection:
    """
    Get database connection instance (dependency injection)
    
    Returns:
        DatabaseConnection singleton instance
    """
    return DatabaseConnection()

"""
Database configuration management
Loads database settings from environment or provides defaults
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str
    port: int
    database: str
    username: str
    password: str
    charset: str = 'utf8mb4'
    collation: str = 'utf8mb4_unicode_ci'
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """
        Create configuration from environment variables
        
        Environment variables:
            DB_HOST (default: 127.0.0.1)
            DB_PORT (default: 3306)
            DB_DATABASE (default: insider)
            DB_USERNAME (default: root)
            DB_PASSWORD (default: password)
        """
        return cls(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=int(os.getenv('DB_PORT', '3306')),
            database=os.getenv('DB_DATABASE', 'insider'),
            username=os.getenv('DB_USERNAME', 'root'),
            password=os.getenv('DB_PASSWORD', 'password'),
        )
    
    @classmethod
    def from_dict(cls, config: dict) -> 'DatabaseConfig':
        """Create configuration from dictionary"""
        return cls(
            host=config.get('host', '127.0.0.1'),
            port=config.get('port', 3306),
            database=config.get('database', 'insider'),
            username=config.get('username', 'root'),
            password=config.get('password', 'password'),
            charset=config.get('charset', 'utf8mb4'),
            collation=config.get('collation', 'utf8mb4_unicode_ci'),
        )


# Singleton instance
_db_config: Optional[DatabaseConfig] = None


def get_db_config(reload: bool = False) -> DatabaseConfig:
    """
    Get database configuration (singleton pattern)
    
    Args:
        reload: Force reload configuration from environment
        
    Returns:
        DatabaseConfig instance
    """
    global _db_config
    
    if _db_config is None or reload:
        _db_config = DatabaseConfig.from_env()
    
    return _db_config


def set_db_config(config: DatabaseConfig):
    """
    Set custom database configuration
    
    Args:
        config: DatabaseConfig instance
    """
    global _db_config
    _db_config = config

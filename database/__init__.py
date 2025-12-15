"""
Database package for InsiderAI Core
Provides centralized database configuration and dependency injection
"""

from .connection import DatabaseConnection, get_db
from .config import get_db_config, DatabaseConfig, set_db_config

__all__ = ['DatabaseConnection', 'get_db', 'get_db_config', 'DatabaseConfig', 'set_db_config']

# =======================================================================================
# app/database.py - Database Management
# =======================================================================================
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
from .config import config

class DatabaseManager:
    """Manages database connections and transactions."""
    
    def __init__(self):
        self.engine: Engine = create_engine(
            config.DB_URL,
            poolclass=QueuePool,
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            isolation_level="READ COMMITTED",
            future=True,
        )
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        with self.engine.begin() as conn:
            yield conn
    
    def execute_query(self, query: str, params: dict = None):
        """Execute a query with parameters."""
        with self.get_connection() as conn:
            return conn.execute(text(query), params or {})
    
    def fetch_one(self, query: str, params: dict = None):
        """Fetch a single result."""
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            return result.mappings().first()
    
    def fetch_all(self, query: str, params: dict = None):
        """Fetch all results."""
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            return result.mappings().all()
        
# Global database instance
db_manager = DatabaseManager()
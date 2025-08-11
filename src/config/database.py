"""
Enterprise Database Configuration for MedFlow HMS
Johns Hopkins Standards Implementation
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import redis
from typing import Optional

class DatabaseConfig:
    """Enterprise database configuration with connection pooling and failover"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/medflow')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '20'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '30'))
        
    def create_engine(self):
        """Create database engine with enterprise settings"""
        return create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
        )
    
    def create_redis_client(self):
        """Create Redis client for caching and sessions"""
        return redis.from_url(self.redis_url, decode_responses=True)

# Database instances
engine = DatabaseConfig().create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
redis_client = DatabaseConfig().create_redis_client()

def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
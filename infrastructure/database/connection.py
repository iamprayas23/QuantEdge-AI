"""Database Connection and Session Management"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://quant:quantpass@localhost:5432/quantedge")


def create_db_engine(url: str = None):
    db_url = url or get_database_url()
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for injecting db session in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

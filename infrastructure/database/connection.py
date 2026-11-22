"""Database Connection and Session Management"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("quantedge.database")


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://quant:quantpass@localhost:5432/quantedge")


def create_db_engine(url: str = None):
    db_url = url or get_database_url()
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )

    # For PostgreSQL, verify connection; if offline, fallback to SQLite
    try:
        test_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2},
        )
        with test_engine.connect():
            pass
        return test_engine
    except Exception as e:
        fallback_url = "sqlite:///./quantedge.db"
        logger.warning(
            f"Could not connect to PostgreSQL at {db_url} ({e}). "
            f"Falling back to local SQLite database at {fallback_url}"
        )
        return create_engine(
            fallback_url,
            connect_args={"check_same_thread": False},
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

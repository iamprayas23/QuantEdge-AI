"""Pytest Configuration and Fixtures"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force SQLite for test suite
os.environ["DATABASE_URL"] = "sqlite:///./test_quantedge_suite.db"
os.environ["USE_IN_MEMORY_QUEUE"] = "true"

from infrastructure.database.models import Base
from infrastructure.database.connection import get_db
from main import app

test_engine = create_engine(
    "sqlite:///./test_quantedge_suite.db",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    try:
        if os.path.exists("./test_quantedge_suite.db"):
            os.remove("./test_quantedge_suite.db")
    except Exception:
        pass


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

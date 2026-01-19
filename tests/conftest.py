"""

Configuration for pytest to set up a test database and provide a TestClient for the FastAPI app.



import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared import Base, get_db
from app import app

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_shared.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override dependency
def override_get_db():

    Dependency override to provide a database session for testing.
    Yields:
        db: SQLAlchemy Session connected to the test database


    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():

    Pytest fixture to provide a TestClient for the FastAPI app with a test database.
    Sets up the database schema before tests and tears it down afterward.
    Yields:
        TestClient: FastAPI TestClient instance


    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
"""
"""

Configuration for pytest to set up a test database and provide a TestClient for the FastAPI app.

"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.company import Company
from shared import Base, get_db
from app import app

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_shared.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def db_session():
    """
    Pytest fixture to provide a database session for testing.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    """
    Pytest fixture to provide a TestClient for the FastAPI app with a test database.
    Sets up the database schema before tests and tears it down afterward.
    Yields:
        TestClient: FastAPI TestClient instance

    """
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        with TestingSessionLocal() as db:
            # Ensure the passcode used in tests exists in the DB
            if not db.query(Company).filter_by(password="1234").first():
                db.add(Company(password="1234", company="Test Company"))
                db.commit()
        yield c
    Base.metadata.drop_all(bind=engine)

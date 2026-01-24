"""

Configuration for pytest to set up a test database and provide a TestClient for the FastAPI app.

"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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


@app.get("/_test/session")
def _test_session(request: Request):
    return {"match_results": request.session.get("match_results")}

@pytest.fixture()
def client(db_session, monkeypatch):
    # Ensure tables exist (reset DB)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # override DB dependency
    # def override_get_db():
    #     yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # monkeypatch extract_text + scoring to be deterministic
    monkeypatch.setattr("app.extract_text_from_pdf", lambda _: "RESUME TEXT")

    # IMPORTANT: calculate_match_score(text, job) in your code
    # We'll return based on job.title or job.id
    def fake_score(text, job):
        # assign deterministic scores
        mapping = {
            "A": 10,
            "B": 90,
            "C": 50,
            "D": 70,
        }
        return mapping.get(job.title, 0)

    monkeypatch.setattr("app.calculate_match_score", fake_score)

    return TestClient(app)
"""

Configuration for pytest to set up a test database and provide a TestClient for the FastAPI app.

"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared import Base, get_db
from app import app

from shared import Base
from models.company import Company
from models.job import Job

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
                db.add_all([
                    Job(
                        title="Backend Engineer",
                        company="Demo Company A",
                        degree="Bachelor",
                        experience="3",
                        required_skills="Python, FastAPI",
                        job_text="Build APIs",
                        id_text="A-1",  # NOT NULL
                        skills_weight=30,
                        degree_weight=40,
                        experience_weight=30,
                        weight_general=100,
                    ),
                    Job(
                        title="Data Engineer",
                        company="Demo Company A",
                        degree="Master",
                        experience="2",
                        required_skills="SQL, ETL",
                        job_text="Pipelines",
                        id_text="A-2",
                        skills_weight=30,
                        degree_weight=40,
                        experience_weight=30,
                        weight_general=100,
                    ),
                    Job(
                        title="Frontend Engineer",
                        company="Demo Company B",
                        degree="Bachelor",
                        experience="1",
                        required_skills="React, JS",
                        job_text="UI work",
                        id_text="B-1",
                        skills_weight=30,
                        degree_weight=40,
                        experience_weight=30,
                        weight_general=100,
                    ),
                ])
                db.add_all([
                    Company(id=5555, company="Demo Company A", password="1111"),
                    Company(id=6666, company="Demo Company B", password="2222"),
                ])

                db.commit()
        yield c
    Base.metadata.drop_all(bind=engine)

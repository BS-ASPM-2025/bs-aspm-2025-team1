# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app import app
from shared import Base, get_db
from models import Company, Job


@pytest.fixture()
def db_session():
    """
    Creates a fresh in-memory SQLite DB for each test.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        # Seed 2 companies
        c1 = Company(id=1111, company="Demo Company A", password="1111")
        c2 = Company(id=2222, company="Demo Company B", password="2222")
        db.add_all([c1, c2])
        db.commit()

        # Seed jobs: 2 for A, 1 for B
        j1 = Job(
            title="Backend Engineer",
            company="Demo Company A",
            degree="Bachelor",
            experience="3",
            required_skills="Python, FastAPI",
            job_text="Build APIs",
            skills_weight=30,
            degree_weight=40,
            experience_weight=30,
            weight_general=100,
        )
        j2 = Job(
            title="Data Engineer",
            company="Demo Company A",
            degree="Master",
            experience="2",
            required_skills="SQL, ETL",
            job_text="Pipelines",
            skills_weight=30,
            degree_weight=40,
            experience_weight=30,
            weight_general=100,
        )
        j3 = Job(
            title="Frontend Engineer",
            company="Demo Company B",
            degree="Bachelor",
            experience="1",
            required_skills="React, JS",
            job_text="UI work",
            skills_weight=30,
            degree_weight=40,
            experience_weight=30,
            weight_general=100,
        )
        db.add_all([j1, j2, j3])
        db.commit()

        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    """
    TestClient with dependency override for get_db.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

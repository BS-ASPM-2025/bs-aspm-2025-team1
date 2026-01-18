"""

Configuration for pytest to set up a test database and provide a TestClient for the FastAPI app.

"""
import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
import app as app_module
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

@pytest.fixture(scope="session", autouse=True)
def _force_project_root_cwd():
    # move cwd to project root (one level above tests/)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(root)

# Override dependency
def override_get_db():
    """
    Dependency override to provide a database session for testing.
    Yields:
        db: SQLAlchemy Session connected to the test database

    """
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    """
    Pytest fixture to provide a TestClient for the FastAPI app with a test database.
    Sets up the database schema before tests and tears it down afterward.
    Yields:
        TestClient: FastAPI TestClient instance

    """
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

#--------------------------------------------------------------------

def _init_jobs_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_text TEXT,
        id_text TEXT,
        title TEXT,
        company TEXT,
        required_skills TEXT,
        degree TEXT,
        experience TEXT,
        skills_weight FLOAT,
        degree_weight FLOAT
    );
    """)
    conn.commit()


@pytest.fixture()
def client(tmp_path):
    # Create a temporary SQLite DB file for the test
    db_path = tmp_path / "test_my_database.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_jobs_schema(conn)
    conn.close()

    # Override the dependency so the route uses the temp DB
    def override_get_sqlite_conn():
        c = sqlite3.connect(str(db_path), check_same_thread=False)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    app_module.app.dependency_overrides[app_module.get_sqlite_conn] = override_get_sqlite_conn

    with TestClient(app_module.app) as test_client:
        yield test_client

    app_module.app.dependency_overrides.clear()


@pytest.fixture()
def db_path(tmp_path):
    # If you want direct DB access in tests, reuse same tmp_path logic per-test
    return tmp_path / "test_my_database.db"
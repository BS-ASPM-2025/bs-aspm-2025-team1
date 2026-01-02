
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared import Base, get_db
from app import app

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_post_job.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def test_post_job_success(client):
    job_data = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "degree": "Bachelor",
        "experience": "3",
        "required_skills": "Python, FastApi",
        "job_text": "We are looking for a developer..."
    }
    
    response = client.post("/post_job", data=job_data)
    
    # Expect redirect to home page, which returns 200 OK (TestClient follows redirects)
    assert response.status_code == 200
    # Check if we landed on the home page (look for "ResMe" which user updated)
    assert "ResMe" in response.text

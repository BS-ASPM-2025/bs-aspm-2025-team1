
import pytest
from app import app
# client fixture is provided by conftest.py


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

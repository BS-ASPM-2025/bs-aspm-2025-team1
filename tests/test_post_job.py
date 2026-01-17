
import pytest
from app import app
# client fixture is provided by conftest.py


def test_post_job_post_requires_company_session(client):
    job_data = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "degree": "Bachelor",
        "experience": "3",
        "required_skills": "Python, FastApi",
        "job_text": "We are looking for a developer..."
    }

    r = client.post("/post_job", data=job_data, follow_redirects=False)

    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/company/login"

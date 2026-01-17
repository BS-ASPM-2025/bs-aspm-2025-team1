"""

Tests for the /post_job endpoint to ensure it requires a company session.

"""
# client fixture is provided by conftest.py


def test_post_job_post_requires_company_session(client):
    """
    Tests that posting a job without a company session redirects to log in.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
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

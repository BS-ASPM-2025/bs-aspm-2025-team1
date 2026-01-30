"""

Tests for the /post_job endpoint to ensure it requires a company session
and covers app.py post_job handler (lines 421-454).

"""
# client fixture is provided by conftest.py

from unittest.mock import patch

LOGIN_URL = "/passcode"
POST_JOB_URL = "/post_job"

# Minimal valid form data for post_job
JOB_FORM_DATA = {
    "title": "Software Engineer",
    "degree": "Bachelor",
    "experience": "3",
    "required_skills": "Python, FastAPI",
    "job_text": "We are looking for a developer...",
    "skills_weight": "25",
    "degree_weight": "25",
    "experience_weight": "25",
    "weight_general": "25",
}


def test_post_job_post_requires_company_session(client):
    """
    Tests that posting a job without a company session redirects to log in.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.post("/post_job", data=JOB_FORM_DATA, follow_redirects=False)

    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/passcode?next=/post_job"


def test_post_job_post_success_redirects_to_feedback(client):
    """
    Tests that authenticated POST creates a job and redirects to post_job_feedback.
    Covers app.py post_job (lines 421-454) happy path.
    """
    # 1. Login (conftest ensures password "1234" exists for Test Company)
    client.post(LOGIN_URL, data={"password": "1234"}, follow_redirects=False)

    # 2. POST job
    r = client.post(POST_JOB_URL, data=JOB_FORM_DATA, follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == "/post_job_feedback"

    # 3. Follow redirect and verify feedback page
    r2 = client.get(r.headers["location"])
    assert r2.status_code == 200
    assert "Software Engineer" in r2.text or "Test Company" in r2.text


def test_post_job_post_value_error_returns_400(client):
    """
    Tests that when create_offer raises ValueError, handler returns 400.
    Covers app.py post_job (lines 435-436) except block.
    """
    # 1. Login
    client.post(LOGIN_URL, data={"password": "1234"}, follow_redirects=False)

    # 2. Mock create_offer to raise ValueError
    with patch("app._job_service.create_offer") as mock_create:
        mock_create.side_effect = ValueError("Company with id=999 not found")

        r = client.post(POST_JOB_URL, data=JOB_FORM_DATA)

    assert r.status_code == 400
    assert "Company with id=999 not found" in r.text

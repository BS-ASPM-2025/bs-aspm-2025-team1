"""

Tests for navigation between different pages of the FastAPI application.

"""
from src.web.auth_controller import templates


def test_index_loads(client):
    """
    Tests that the index page loads successfully.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.get("/")
    assert r.status_code == 200
    assert "Unlock Your Career" in r.text

def test_passcode_get_loads(client):
    """
    Tests that the passcode page loads successfully.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.get("/passcode")
    assert r.status_code == 200
    assert "Password" in r.text

def test_passcode_post_redirects_to_post_job(client):
    """
    Tests that submitting the passcode redirects to the post job page.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.post("/passcode", data={"password": "1234"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/post_job"

def test_post_job_get_requires_company_session(client):
    """
    Tests that accessing the post job page without a company session redirects to log in.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.get("/post_job", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/company/login"

def test_company_login_get_loads(client):
    """
    Tests that the company login page loads successfully.
    :param client: TestClient fixture provided by conftest.py
    """
    r = client.get("/company/login")
    print("TEMPLATES SEARCHPATH:", templates.env.loader.searchpath)
    assert r.status_code == 200

def upload_resume_job_get_loads(client):
    """
    Tests that the upload resume page loads successfully.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.get("/upload_resume")
    assert r.status_code == 200
    assert "Upload Resume" in r.text


def test_upload_resume_loads(client):
    """
    Tests that the upload resume page loads successfully.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.get("/upload_resume")
    assert r.status_code == 200
    assert "Upload Resume" in r.text

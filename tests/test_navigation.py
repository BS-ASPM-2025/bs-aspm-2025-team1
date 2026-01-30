"""

Tests for navigation between different pages of the FastAPI application.

"""

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
    Tests that submitting the passcode redirects to the post-job page.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.post("/passcode", data={"password": "1234"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/post_job" in r.headers["location"]

def test_post_job_get_requires_company_session(client):
    """
    Tests that accessing the post-job page without a company session redirects to log in.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.get("/post_job", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/passcode?next=/post_job"

def test_company_login_get_loads(client):
    """
    Tests that the company login page loads successfully.
    :param client: TestClient fixture provided by conftest.py
    """
    r = client.get("/passcode")
    assert r.status_code == 200

def test_upload_resume_job_get_loads(client):
    """
    Tests that the upload resume page loads successfully.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    r = client.get("/upload_resume")
    assert r.status_code == 200
    assert "Upload Resume" in r.text


def test_jobs_list_loads(client):
    """
    Tests that the jobs list page loads successfully.
    """
    r = client.get("/jobs_list")
    assert r.status_code == 200
    assert "Jobs List" in r.text


def test_hr_jobs_list_loads(client):
    """
    Tests that the HR jobs list page loads successfully.
    """
    r = client.get("/hr_jobs_list")
    assert r.status_code == 200
    assert "Jobs List" in r.text


def test_logout_redirects_to_home(client):
    """
    Tests that logout redirects to the home page.
    """
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/"


def test_index_has_navigation_links(client):
    """
    Tests that the index page contains links to upload resume and post job.
    """
    r = client.get("/")
    assert r.status_code == 200
    assert "/upload_resume" in r.text
    assert "/post_job" in r.text

# tests/test_navigation.py

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_index_loads():
    r = client.get("/")
    assert r.status_code == 200
    assert "Unlock Your Career" in r.text

def test_passcode_get_loads():
    r = client.get("/passcode")
    assert r.status_code == 200
    assert "Password" in r.text

def test_passcode_post_redirects_to_post_job():
    r = client.post("/passcode", data={"password": "1234"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/post_job"

def test_post_job_get_loads():
    r = client.get("/post_job")
    assert r.status_code == 200

def upload_resume_job_get_loads():
    r = client.get("/upload_resume")
    assert r.status_code == 200
    assert "Upload Resume" in r.text


def test_upload_resume_loads():
    r = client.get("/upload_resume")
    assert r.status_code == 200
    assert "Upload Resume" in r.text
"""

Tests for authentication and security features of the job posting application.

"""

import pytest
import time
from unittest.mock import patch
from models.company import Company
from models.job import Job
from src.security.passwords import hash_password
from tests.conftest import TestingSessionLocal
from src.security.session import SESSION_TTL_SECONDS

@pytest.fixture(autouse=True)
def run_around_tests(client):
    # Setup: Ensure clean session
    client.cookies.clear()
    
    # Teardown: Clean up tables after each test
    yield
    db = TestingSessionLocal()
    try:
        db.query(Job).delete()
        db.query(Company).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def create_company(name, password):
    db = TestingSessionLocal()
    hashed = hash_password(password)
    company = Company(company_name=name, password=hashed)
    db.add(company)
    db.commit()
    db.refresh(company)
    db.close()
    return company

def test_login_success_creates_session(client):
    """Verify Session/token is created on successful password entry"""
    create_company("AuthUser", "password123")
    
    response = client.post("/auth/company", data={
        "company_name": "AuthUser",
        "password": "password123"
    }, follow_redirects=False)
    
    # Should redirect to dashboard
    assert response.status_code == 303
    assert response.headers["location"] == "/jobs/manage"
    
    # Session cookie should be set
    assert "session" in response.cookies
    assert response.cookies["session"] is not None

def test_protected_endpoints_reject_unauthorized(client):
    """Protected endpoints/pages reject unauthorized users"""
    # Try accessing the protected page without a login
    paths = [
        "/jobs/manage",
        "/post_job",
    ]
    
    for path in paths:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert "/company/login" in response.headers["location"]

def test_company_isolation(client):
    """Company isolation (cannot access another company by URL)"""
    create_company("CompanyA", "passA")
    create_company("CompanyB", "passB")
    
    # Login as Company A
    client.post("/auth/company", data={"company_name": "CompanyA", "password": "passA"})
    
    # Create a job for Company B strictly manually to ensure it belongs to B
    db = TestingSessionLocal()
    job_b = Job(
        title="Job for B",
        job_text="Secret text",
        id_text="job-b-uuid",
        company="CompanyB",  # Belongs to B
        required_skills="None",
        degree="None",
        experience="None"
    )
    db.add(job_b)
    db.commit()
    db.refresh(job_b)
    job_id_b = job_b.id
    db.close()
    
    # Try to edit Company B's job while logged in as A
    response_edit = client.get(f"/jobs/{job_id_b}/edit")
    # Should be 403 Forbidden
    assert response_edit.status_code == 403
    
    # Try to delete Company B's job while logged in as A
    response_delete = client.post(f"/jobs/{job_id_b}/delete")
    assert response_delete.status_code == 403

def test_session_expiration(client):
    """Session expiration behavior"""
    create_company("TimeCo", "timetravel")
    
    # Login
    client.post("/auth/company", data={"company_name": "TimeCo", "password": "timetravel"})
    
    # Verify access is granted initially
    resp_ok = client.get("/jobs/manage", follow_redirects=False)
    assert resp_ok.status_code == 200
    
    # Simulate time passing beyond TTL
    future_time = time.time() + SESSION_TTL_SECONDS + 60
    
    # We patch inside src.security.session where checking happens
    with patch("src.security.session.time.time", return_value=future_time):
        resp_expired = client.get("/jobs/manage", follow_redirects=False)
        assert resp_expired.status_code == 303
        assert "/company/login" in resp_expired.headers["location"]

def test_logout_invalidates_session(client):
    """Logout invalidates session"""
    create_company("LeaverCo", "bye")
    
    # Login
    client.post("/auth/company", data={"company_name": "LeaverCo", "password": "bye"})
    
    # Verify access
    assert client.get("/jobs/manage").status_code == 200
    
    # Logout
    client.post("/logout")
    
    # Verify session is cleared/invalidated
    # Cookie might still be there but empty, or the server rejects it.
    resp = client.get("/jobs/manage", follow_redirects=False)
    assert resp.status_code == 303
    assert "/company/login" in resp.headers["location"]

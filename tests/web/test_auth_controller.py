# tests/web/test_auth_controller.py

from dataclasses import dataclass
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared import get_db
import src.web.auth_controller as auth_controller


# ----------------------------
# Fakes / helpers
# ----------------------------

@dataclass
class FakeCompany:
    id: int


@dataclass
class FakeJobSeeker:
    id: int
    email: str = "test.jobseeker@example.com"


class FakeAuthService:
    """
    Generic fake for CompanyAuthService / JobSeekerAuthService.
    Records calls to authenticate() and returns configurable result.
    """
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.calls = []  # list of tuples: (method_name, kwargs)

    def authenticate(self, db, login_value: str, password: str):
        self.calls.append(("authenticate", {"login_value": login_value, "password": password}))
        return self.return_value


class CallRecorder:
    def __init__(self):
        self.calls = []

    def record(self, name: str, **kwargs):
        self.calls.append((name, kwargs))


def make_test_app(monkeypatch):
    app = FastAPI()
    app.include_router(auth_controller.router)

    # 1) Mock DB dependency
    def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db

    # 2) Mock auth services
    fake_company_auth = FakeAuthService()
    fake_jobseeker_auth = FakeAuthService()

    monkeypatch.setattr(auth_controller, "_company_auth_service", fake_company_auth)
    monkeypatch.setattr(auth_controller, "_jobseeker_auth_service", fake_jobseeker_auth)

    # 3) Mock session functions
    recorder = CallRecorder()

    def fake_start_company_session(request, company_id: int):
        recorder.record("start_company_session", company_id=company_id)

    def fake_start_jobseeker_session(request, jobseeker_id: int):
        recorder.record("start_jobseeker_session", jobseeker_id=jobseeker_id)

    def fake_logout(request):
        recorder.record("logout")

    monkeypatch.setattr(auth_controller, "start_company_session", fake_start_company_session)
    monkeypatch.setattr(auth_controller, "start_jobseeker_session", fake_start_jobseeker_session)
    monkeypatch.setattr(auth_controller, "logout", fake_logout)

    return app, fake_company_auth, fake_jobseeker_auth, recorder


# ============================================================
# GET login pages (basic rendering + error mapping)
# ============================================================

def test_get_company_login_page_happy_path(monkeypatch):
    app, _, __, ___ = make_test_app(monkeypatch)
    client = TestClient(app)

    resp = client.get("/company/login", follow_redirects=False)
    assert resp.status_code == 200


def test_get_company_login_page_invalid_credentials_message(monkeypatch):
    app, _, __, ___ = make_test_app(monkeypatch)
    client = TestClient(app)

    resp = client.get("/company/login?err=invalid_credentials", follow_redirects=False)
    assert resp.status_code == 200

    # If your template prints {{ error }}, this will be present.
    assert "Invalid company name or password" in resp.text


def test_get_jobseeker_login_page_invalid_credentials_message(monkeypatch):
    app, _, __, ___ = make_test_app(monkeypatch)
    client = TestClient(app)

    resp = client.get("/jobseeker/login?err=invalid_credentials", follow_redirects=False)
    assert resp.status_code == 200
    assert "Invalid email or password" in resp.text


# ============================================================
# POST /auth/company
# ============================================================

def test_post_auth_company_happy_path(monkeypatch):
    app, fake_company_auth, _, recorder = make_test_app(monkeypatch)
    client = TestClient(app)

    fake_company_auth.return_value = FakeCompany(id=777)

    form = {
        "company_name": "  ResMe  ",  # verify strip
        "password": "secret",
    }

    resp = client.post("/auth/company", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobs/manage"

    # authenticate() called with stripped company_name
    assert len(fake_company_auth.calls) == 1
    name, kwargs = fake_company_auth.calls[0]
    assert name == "authenticate"
    assert kwargs["login_value"] == "ResMe"
    assert kwargs["password"] == "secret"

    # session started
    assert recorder.calls == [("start_company_session", {"company_id": 777})]


def test_post_auth_company_invalid_credentials(monkeypatch):
    app, fake_company_auth, _, recorder = make_test_app(monkeypatch)
    client = TestClient(app)

    fake_company_auth.return_value = None

    form = {"company_name": "ResMe", "password": "bad"}

    resp = client.post("/auth/company", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/company/login?err=invalid_credentials"

    # session must NOT be started
    assert recorder.calls == []


# ============================================================
# POST /auth/jobseeker
# ============================================================

def test_post_auth_jobseeker_happy_path(monkeypatch):
    app, _, fake_jobseeker_auth, recorder = make_test_app(monkeypatch)
    client = TestClient(app)

    fake_jobseeker_auth.return_value = FakeJobSeeker(id=123, email="test.jobseeker@example.com")

    form = {
        "email": "  test.jobseeker@example.com  ",  # verify strip
        "password": "secret",
    }

    resp = client.post("/auth/jobseeker", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/manage"

    # authenticate() called with stripped email
    assert len(fake_jobseeker_auth.calls) == 1
    name, kwargs = fake_jobseeker_auth.calls[0]
    assert name == "authenticate"
    assert kwargs["login_value"] == "test.jobseeker@example.com"
    assert kwargs["password"] == "secret"

    # session started
    assert recorder.calls == [("start_jobseeker_session", {"jobseeker_id": 123})]


def test_post_auth_jobseeker_invalid_credentials(monkeypatch):
    app, _, fake_jobseeker_auth, recorder = make_test_app(monkeypatch)
    client = TestClient(app)

    fake_jobseeker_auth.return_value = None

    form = {"email": "x@y.com", "password": "bad"}

    resp = client.post("/auth/jobseeker", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobseeker/login?err=invalid_credentials"
    assert recorder.calls == []


# ============================================================
# POST /logout
# ============================================================

def test_post_logout_redirects_to_home(monkeypatch):
    app, _, __, recorder = make_test_app(monkeypatch)
    client = TestClient(app)

    resp = client.post("/logout", data={}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    assert recorder.calls == [("logout", {})]

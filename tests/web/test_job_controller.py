# tests/test_job_controller.py

from dataclasses import dataclass
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared import get_db
from src.security.session import require_company_session
import src.web.job_controller as job_controller


@dataclass
class FakeJob:
    id: int
    company_id: int
    raw_text: str | None = None
    title: str | None = None
    required_skills: str | None = None
    degree: str | None = None
    experience: str | None = None


class FakeJobService:
    def __init__(self):
        self.calls = []

        # Optional: allow tests to force errors on specific methods
        self.raise_on = {}  # e.g. {"create_offer": ValueError("...")}

    def _record(self, name: str, **kwargs):
        self.calls.append((name, kwargs))

    def _maybe_raise(self, name: str):
        exc = self.raise_on.get(name)
        if exc is not None:
            raise exc

    # used by POST /post_job
    def create_offer(self, db, **kwargs):
        self._maybe_raise("create_offer")
        self._record("create_offer", **kwargs)
        return FakeJob(id=1, company_id=kwargs["company_id"], raw_text="Description:\nX")

    # used by GET /jobs/manage
    def list_jobs_for_company(self, db, company_id: int):
        self._maybe_raise("list_jobs_for_company")
        self._record("list_jobs_for_company", company_id=company_id)
        return [
            FakeJob(id=10, company_id=company_id, title="Job A"),
            FakeJob(id=11, company_id=company_id, title="Job B"),
        ]

    # used by GET /jobs/{job_id}/edit
    def get_offer_for_company(self, db, *, company_id: int, job_id: int):
        self._maybe_raise("get_offer_for_company")
        self._record("get_offer_for_company", company_id=company_id, job_id=job_id)
        return FakeJob(
            id=job_id,
            company_id=company_id,
            raw_text="Title: T\n\nDescription:\nHello world",
            title="T",
        )

    # used by POST /jobs/{job_id}/edit
    def update_offer(self, db, **kwargs):
        self._maybe_raise("update_offer")
        self._record("update_offer", **kwargs)
        return FakeJob(
            id=kwargs["job_id"],
            company_id=kwargs["company_id"],
            raw_text="Description:\nUpdated",
        )

    # used by POST /jobs/{job_id}/delete
    def delete_offer(self, db, *, company_id: int, job_id: int):
        self._maybe_raise("delete_offer")
        self._record("delete_offer", company_id=company_id, job_id=job_id)
        return None


def make_test_app(monkeypatch, *, company_id: int = 123):
    app = FastAPI()
    app.include_router(job_controller.router)

    # 1) Mock session dependency
    app.dependency_overrides[require_company_session] = lambda: company_id

    # 2) Mock DB dependency
    def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db

    # 3) Mock service (avoid DB / repositories)
    fake_service = FakeJobService()
    monkeypatch.setattr(job_controller, "_job_service", fake_service)

    return app, fake_service


# ============================================================
# Positive flow (happy paths)
# ============================================================

def test_get_post_job_page_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    resp = client.get("/post_job", follow_redirects=False)

    assert resp.status_code == 200
    # TemplateResponse returns HTML; happy path here is: no redirect and no crash
    assert fake_service.calls == []  # service must not be called for the form page


def test_post_job_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    form = {
        "title": "Junior Python Dev",
        "degree": "BSc",
        "experience": "0-1 years",
        "required_skills": "Python, FastAPI",
        "job_text": "We need a junior dev",
        "skills_weight": "1.0",
        "degree_weight": "1.0",
        "experience_weight": "1.0",
        "weight_general": "1.0",
    }

    resp = client.post("/post_job", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobs/manage?success=1"

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "create_offer"
    assert kwargs["company_id"] == 777
    assert kwargs["title"] == "Junior Python Dev"
    assert kwargs["degree"] == "BSc"


def test_get_post_job_feedback_page_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    resp = client.get("/post_job_feedback", follow_redirects=False)

    assert resp.status_code == 200
    assert fake_service.calls == []


def test_get_jobs_manage_page_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    resp = client.get("/jobs/manage", follow_redirects=False)

    assert resp.status_code == 200

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "list_jobs_for_company"
    assert kwargs["company_id"] == 777


def test_get_job_edit_page_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    resp = client.get("/jobs/42/edit", follow_redirects=False)

    assert resp.status_code == 200

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "get_offer_for_company"
    assert kwargs["company_id"] == 777
    assert kwargs["job_id"] == 42


def test_post_job_update_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    # Send only part of the fields (Optional). Others will be None.
    form = {
        "title": "Updated title",
        "job_text": "Updated description",
        "skills_weight": "2.5",
    }

    resp = client.post("/jobs/42/edit", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobs/manage?updated=1"

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "update_offer"
    assert kwargs["company_id"] == 777
    assert kwargs["job_id"] == 42
    assert kwargs["title"] == "Updated title"
    # skills_weight should be a float after normalization
    assert kwargs["skills_weight"] == 2.5
    assert kwargs["job_text"] == "Updated description"


def test_post_job_delete_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    resp = client.post("/jobs/42/delete", data={}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobs/manage?deleted=1"

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "delete_offer"
    assert kwargs["company_id"] == 777
    assert kwargs["job_id"] == 42


# ============================================================
# Negative flow (error handling paths)
# ============================================================

def test_post_job_redirects_on_value_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    # Controller catches ValueError and redirects to /jobs/manage?error=...
    fake_service.raise_on["create_offer"] = ValueError("Invalid job title")

    form = {
        "title": "X",
        "degree": "BSc",
        "experience": "0-1 years",
        "required_skills": "Python",
        "job_text": "Text",
    }

    resp = client.post("/post_job", data=form, follow_redirects=False)

    assert resp.status_code == 303
    # error message is URL-quoted by controller
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Invalid%20job%20title" in resp.headers["location"]
    # Ensure the service method was not recorded after raising
    assert fake_service.calls == []


def test_get_job_edit_redirects_on_permission_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["get_offer_for_company"] = PermissionError("Not your job")

    resp = client.get("/jobs/42/edit", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Not%20your%20job" in resp.headers["location"]
    assert fake_service.calls == []


def test_get_job_edit_redirects_on_value_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["get_offer_for_company"] = ValueError("Job offer not found")

    resp = client.get("/jobs/999/edit", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Job%20offer%20not%20found" in resp.headers["location"]
    assert fake_service.calls == []


def test_post_job_update_redirects_on_permission_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["update_offer"] = PermissionError("Job offer does not belong to this company")

    form = {"title": "Updated title"}

    resp = client.post("/jobs/42/edit", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Job%20offer%20does%20not%20belong%20to%20this%20company" in resp.headers["location"]
    assert fake_service.calls == []


def test_post_job_update_redirects_on_value_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["update_offer"] = ValueError("Job offer not found")

    form = {"title": "Updated title"}

    resp = client.post("/jobs/999/edit", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Job%20offer%20not%20found" in resp.headers["location"]
    assert fake_service.calls == []


def test_post_job_delete_redirects_on_permission_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["delete_offer"] = PermissionError("Not allowed")

    resp = client.post("/jobs/42/delete", data={}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Not%20allowed" in resp.headers["location"]
    assert fake_service.calls == []


def test_post_job_delete_redirects_on_value_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["delete_offer"] = ValueError("Job offer not found")

    resp = client.post("/jobs/999/delete", data={}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Job%20offer%20not%20found" in resp.headers["location"]
    assert fake_service.calls == []

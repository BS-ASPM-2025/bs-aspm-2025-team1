# tests/web/test_match_controller.py

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import HTMLResponse

from shared import get_db
from src.security.session import require_company_session
import src.web.match_controller as match_controller


# -------------------------------
# Fakes
# -------------------------------

@dataclass
class FakeJob:
    id: int
    company_id: int
    title: str | None = None


@dataclass
class FakeMatchListItem:
    match_id: int
    resume_id: int
    resume_title: str
    job_seeker_id: int | None
    score_percent: int
    created_at: str | None = None


class FakeMatchService:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.raise_on: dict[str, Exception] = {}

        self.job_to_return = FakeJob(id=1, company_id=1, title="Job")
        self.matches_to_return: list[FakeMatchListItem] = [
            FakeMatchListItem(
                match_id=1,
                resume_id=10,
                resume_title="CV 10",
                job_seeker_id=100,
                score_percent=80,
                created_at="2026-01-20",
            )
        ]

    def _record(self, name: str, **kwargs):
        self.calls.append((name, kwargs))

    def _maybe_raise(self, name: str):
        exc = self.raise_on.get(name)
        if exc is not None:
            raise exc

    # used by GET /jobs/{job_id}/matches
    def list_view_for_job(self, db, *, session_company_id: int, job_id: int, limit: int = 50):
        self._maybe_raise("list_view_for_job")
        self._record(
            "list_view_for_job",
            session_company_id=session_company_id,
            job_id=job_id,
            limit=limit,
        )
        return self.job_to_return, self.matches_to_return

    # used by POST /jobs/{job_id}/matches/recompute
    def recompute_for_job(self, db, *, session_company_id: int, job_id: int, top_k: int = 50, resumes_limit=None):
        self._maybe_raise("recompute_for_job")
        self._record(
            "recompute_for_job",
            session_company_id=session_company_id,
            job_id=job_id,
            top_k=top_k,
            resumes_limit=resumes_limit,
        )
        return []


# -------------------------------
# App factory
# -------------------------------

def make_test_app(monkeypatch, *, company_id: int = 123):
    app = FastAPI()
    app.include_router(match_controller.router)

    # 1) Override company session dependency
    app.dependency_overrides[require_company_session] = lambda: company_id

    # 2) Override DB dependency
    def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db

    # 3) Patch TemplateResponse to avoid TemplateNotFound (job_matches.html may not exist yet)
    def fake_template_response(*, request, name, context, status_code: int = 200, **kwargs):
        # We don't assert HTML content here; only that controller returns 200 and calls service
        return HTMLResponse("OK", status_code=status_code)

    monkeypatch.setattr(match_controller.templates, "TemplateResponse", fake_template_response)

    # 4) Mock service
    fake_service = FakeMatchService()
    monkeypatch.setattr(match_controller, "_match_service", fake_service)

    return app, fake_service


# ============================================================
# GET /jobs/{job_id}/matches
# ============================================================

def test_get_job_matches_page_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    resp = client.get("/jobs/42/matches", follow_redirects=False)

    assert resp.status_code == 200

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "list_view_for_job"
    assert kwargs["session_company_id"] == 777
    assert kwargs["job_id"] == 42
    assert kwargs["limit"] == 50


def test_get_job_matches_redirects_on_value_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["list_view_for_job"] = ValueError("Job offer not found")

    resp = client.get("/jobs/999/matches", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Job%20offer%20not%20found" in resp.headers["location"]
    assert fake_service.calls == []


def test_get_job_matches_redirects_on_permission_error(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["list_view_for_job"] = PermissionError("Job offer does not belong to this company")

    resp = client.get("/jobs/42/matches", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Job%20offer%20does%20not%20belong%20to%20this%20company" in resp.headers["location"]
    assert fake_service.calls == []


# ============================================================
# POST /jobs/{job_id}/matches/recompute
# ============================================================

def test_post_recompute_job_matches_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    form = {
        "top_k": "25",
        "resumes_limit": "100",
    }

    resp = client.post("/jobs/42/matches/recompute", data=form, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobs/42/matches?recomputed=1"

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "recompute_for_job"
    assert kwargs["session_company_id"] == 777
    assert kwargs["job_id"] == 42
    assert kwargs["top_k"] == 25
    assert kwargs["resumes_limit"] == 100


def test_post_recompute_job_matches_permission_error_redirect(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["recompute_for_job"] = PermissionError("no")

    resp = client.post("/jobs/42/matches/recompute", data={"top_k": "10"}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Access%20denied" in resp.headers["location"]
    assert fake_service.calls == []


def test_post_recompute_job_matches_value_error_redirect(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["recompute_for_job"] = ValueError("not found")

    resp = client.post("/jobs/999/matches/recompute", data={"top_k": "10"}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/jobs/manage?error=")
    assert "Job%20offer%20not%20found" in resp.headers["location"]
    assert fake_service.calls == []


def test_post_recompute_job_matches_generic_exception_redirects_to_err(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, company_id=777)
    client = TestClient(app)

    fake_service.raise_on["recompute_for_job"] = RuntimeError("boom")

    resp = client.post("/jobs/42/matches/recompute", data={"top_k": "10"}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobs/42/matches?err=recompute_failed"
    assert fake_service.calls == []

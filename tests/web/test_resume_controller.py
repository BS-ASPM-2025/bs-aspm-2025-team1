# tests/web/test_resume_controller.py

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared import get_db
import src.web.resume_controller as resume_controller
from src.tools.resume_text_extractor import ResumeExtractionError


@dataclass
class FakeResume:
    id: int
    job_seeker_id: int
    source_id_text: str | None = None
    raw_text: str | None = None
    created_at: str | None = None


class FakeResumeService:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, Any]]] = []

        # Optional forcing errors per method name
        self.raise_on: dict[str, Exception] = {}

        # configurable results
        self.list_result: list[FakeResume] = []
        self.delete_ok: bool = True
        self.get_by_id_result: FakeResume | None = FakeResume(id=1, job_seeker_id=1)
        self.text_view_result: dict[str, Any] = {
            "status": "ok",
            "job_seeker_email": "test.jobseeker@example.com",
            "resume_title": "My CV",
            "resume_id": 1,
            "created_at": "2026-01-19",
            "resume_text": "Hello from resume text",
        }

    def _record(self, name: str, **kwargs):
        self.calls.append((name, kwargs))

    def _maybe_raise(self, name: str):
        exc = self.raise_on.get(name)
        if exc is not None:
            raise exc

    # --- methods used by controller ---

    def list_for_jobseeker(self, db, job_seeker_id: int):
        self._maybe_raise("list_for_jobseeker")
        self._record("list_for_jobseeker", job_seeker_id=job_seeker_id)
        return self.list_result

    def get_by_id(self, db, resume_id: int):
        self._maybe_raise("get_by_id")
        self._record("get_by_id", resume_id=resume_id)
        return self.get_by_id_result

    async def create_from_upload(self, db, job_seeker_id: int, file, title: str):
        self._maybe_raise("create_from_upload")
        self._record(
            "create_from_upload",
            job_seeker_id=job_seeker_id,
            filename=getattr(file, "filename", None),
            content_type=getattr(file, "content_type", None),
            title=title,
        )
        return FakeResume(id=99, job_seeker_id=job_seeker_id, source_id_text=title, raw_text="X")

    def delete_if_owned(self, db, job_seeker_id: int, resume_id: int) -> bool:
        self._maybe_raise("delete_if_owned")
        self._record("delete_if_owned", job_seeker_id=job_seeker_id, resume_id=resume_id)
        return self.delete_ok

    def build_resume_text_view(self, db, job_seeker_id: int, resume_id: int) -> dict[str, Any]:
        self._maybe_raise("build_resume_text_view")
        self._record("build_resume_text_view", job_seeker_id=job_seeker_id, resume_id=resume_id)
        return self.text_view_result


def make_test_app(monkeypatch, *, job_seeker_id: int = 123):
    app = FastAPI()
    app.include_router(resume_controller.router)

    # 1) override DB dependency
    def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db

    # 2) require_jobseeker_session is called directly (not Depends) -> monkeypatch the function in module
    def fake_require_jobseeker_session(request):
        return job_seeker_id

    monkeypatch.setattr(resume_controller, "require_jobseeker_session", fake_require_jobseeker_session)

    # 3) mock service
    fake_service = FakeResumeService()
    monkeypatch.setattr(resume_controller, "_resume_service", fake_service)

    return app, fake_service


# ============================================================
# GET /resumes/manage
# ============================================================

def test_get_resumes_manage_page_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.list_result = [
        FakeResume(id=1, job_seeker_id=777, source_id_text="CV 1"),
        FakeResume(id=2, job_seeker_id=777, source_id_text="CV 2"),
    ]

    resp = client.get("/resumes/manage", follow_redirects=False)

    assert resp.status_code == 200
    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "list_for_jobseeker"
    assert kwargs["job_seeker_id"] == 777


# ============================================================
# GET /resumes/upload
# ============================================================

def test_get_resumes_upload_page_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    resp = client.get("/resumes/upload", follow_redirects=False)

    assert resp.status_code == 200
    # upload page should not call service
    assert fake_service.calls == []


# ============================================================
# POST /resumes/upload
# ============================================================

def test_post_resumes_upload_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    files = {
        "file": ("cv.txt", b"hello", "text/plain"),
    }
    data = {
        "title": "  Backend CV  ",
    }

    resp = client.post("/resumes/upload", data=data, files=files, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/manage?success=1"

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "create_from_upload"
    assert kwargs["job_seeker_id"] == 777
    assert kwargs["title"] == "Backend CV"
    assert kwargs["filename"] == "cv.txt"


def test_post_resumes_upload_title_required(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    files = {"file": ("cv.txt", b"hello", "text/plain")}
    data = {"title": "   "}  # becomes empty after strip

    resp = client.post("/resumes/upload", data=data, files=files, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/upload?err=title_required"
    assert fake_service.calls == []


def test_post_resumes_upload_redirects_on_unsupported_file(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.raise_on["create_from_upload"] = ResumeExtractionError("Unsupported file type")

    files = {"file": ("cv.xyz", b"hello", "application/octet-stream")}
    data = {"title": "My CV"}

    resp = client.post("/resumes/upload", data=data, files=files, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/upload?err=unsupported_file"
    assert fake_service.calls == []


def test_post_resumes_upload_redirects_on_generic_upload_failed(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.raise_on["create_from_upload"] = ResumeExtractionError("Failed to parse DOCX")

    files = {"file": ("cv.docx", b"x", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"title": "My CV"}

    resp = client.post("/resumes/upload", data=data, files=files, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/upload?err=upload_failed"
    assert fake_service.calls == []


# ============================================================
# POST /resumes/{resume_id}/delete
# ============================================================

def test_post_resumes_delete_happy_path(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.delete_ok = True

    resp = client.post("/resumes/42/delete", data={}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/manage?deleted=1"

    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "delete_if_owned"
    assert kwargs["job_seeker_id"] == 777
    assert kwargs["resume_id"] == 42


def test_post_resumes_delete_not_found(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.delete_ok = False
    fake_service.get_by_id_result = None

    resp = client.post("/resumes/999/delete", data={}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/manage?err=not_found"

    assert len(fake_service.calls) == 2
    assert fake_service.calls[0][0] == "delete_if_owned"
    assert fake_service.calls[1][0] == "get_by_id"


def test_post_resumes_delete_access_denied(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.delete_ok = False
    fake_service.get_by_id_result = FakeResume(id=42, job_seeker_id=999)  # exists but not owned

    resp = client.post("/resumes/42/delete", data={}, follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] == "/resumes/manage?err=access_denied"

    assert len(fake_service.calls) == 2
    assert fake_service.calls[0][0] == "delete_if_owned"
    assert fake_service.calls[1][0] == "get_by_id"


# ============================================================
# GET /resumes/{resume_id}/text
# ============================================================

def test_get_resume_text_view_ok(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.text_view_result = {
        "status": "ok",
        "job_seeker_email": "test.jobseeker@example.com",
        "resume_title": "Demo CV",
        "resume_id": 5,
        "created_at": "2026-01-19",
        "resume_text": "Some extracted text",
    }

    resp = client.get("/resumes/5/text", follow_redirects=False)

    assert resp.status_code == 200
    assert len(fake_service.calls) == 1
    name, kwargs = fake_service.calls[0]
    assert name == "build_resume_text_view"
    assert kwargs["job_seeker_id"] == 777
    assert kwargs["resume_id"] == 5


def test_get_resume_text_view_not_found(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.text_view_result = {"status": "not_found"}

    resp = client.get("/resumes/999/text", follow_redirects=False)

    assert resp.status_code == 404
    assert len(fake_service.calls) == 1
    assert fake_service.calls[0][0] == "build_resume_text_view"


def test_get_resume_text_view_access_denied(monkeypatch):
    app, fake_service = make_test_app(monkeypatch, job_seeker_id=777)
    client = TestClient(app)

    fake_service.text_view_result = {"status": "access_denied"}

    resp = client.get("/resumes/5/text", follow_redirects=False)

    assert resp.status_code == 403
    assert len(fake_service.calls) == 1
    assert fake_service.calls[0][0] == "build_resume_text_view"

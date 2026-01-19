# tests/services/test_resume_service.py

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from shared.alembic_runner import upgrade_head

import src.services.resume_service as resume_service_module
from src.repositories.resume_repository import ResumeRepository
from src.repositories.jobseeker_repository import JobSeekerRepository
from src.services.resume_service import ResumeService
from src.tools.resume_text_extractor import ResumeExtractionError
from src.models import Resume


JOBSEEKER_TABLE = "job_seekers"
RESUMES_TABLE = "resumes"


# -------------------------------
# Helpers (DB bootstrap utilities)
# -------------------------------

def _default_value(col_name: str, col_type: str):
    t = (col_type or "").upper()
    name = (col_name or "").lower()

    if "INT" in t:
        return 1
    if "BOOL" in t:
        return 1
    if "DATE" in t or "TIME" in t:
        return datetime.utcnow().isoformat(sep=" ", timespec="seconds")

    if "email" in name:
        return "test.jobseeker@example.com"
    if "password" in name or "hash" in name:
        return "test_hash"
    if "first" in name:
        return "Test"
    if "last" in name:
        return "User"
    if "name" in name:
        return "Test"
    return "test"


def _table_exists(db_file: Path, table: str) -> bool:
    con = sqlite3.connect(str(db_file))
    try:
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None
    finally:
        con.close()


def _insert_minimal_row(db_file: Path, table: str, preset: dict | None = None) -> int:
    """
    Inserts a minimal row into a table by introspecting NOT NULL columns
    (excluding PK) and filling with safe defaults.

    Returns last_insert_rowid() as int.
    """
    preset = preset or {}
    con = sqlite3.connect(str(db_file))
    try:
        cols = con.execute(f'PRAGMA table_info("{table}")').fetchall()
        # cols: (cid, name, type, notnull, dflt_value, pk)

        values = {}
        for _, name, ctype, notnull, dflt, pk in cols:
            if pk == 1:
                continue
            if name in preset:
                values[name] = preset[name]
                continue
            if notnull == 1 and dflt is None:
                values[name] = _default_value(name, ctype)

        if not values:
            con.execute(f'INSERT INTO "{table}" DEFAULT VALUES')
        else:
            col_names = ", ".join([f'"{k}"' for k in values.keys()])
            placeholders = ", ".join(["?"] * len(values))
            con.execute(
                f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})',
                list(values.values()),
            )

        con.commit()
        row_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        return int(row_id)
    finally:
        con.close()


# -------------------------------
# Fake UploadFile (stable for tests)
# -------------------------------

class FakeUploadFile:
    def __init__(self, filename: str, content_type: str | None, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:
        return self._data


# -------------------------------
# Pytest fixtures (engine/session)
# -------------------------------

@pytest.fixture(scope="module")
def test_db(tmp_path_factory, request):
    """
    Creates a temp SQLite DB file and applies Alembic migrations once per module.
    """
    safe_name = request.module.__name__.replace(".", "_")
    db_dir = tmp_path_factory.mktemp("db")
    db_file = db_dir / f"{safe_name}.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    os.environ["DATABASE_URL"] = db_url
    upgrade_head(db_url)

    yield db_url, db_file

    try:
        db_file.unlink()
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def engine(test_db):
    db_url, _ = test_db
    eng = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=False,
    )
    yield eng
    eng.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """
    SAVEPOINT pattern to isolate tests even if code does commit().
    """
    connection = engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def resume_repo():
    return ResumeRepository()


@pytest.fixture()
def jobseeker_repo():
    return JobSeekerRepository()


@pytest.fixture()
def resume_service(resume_repo, jobseeker_repo):
    return ResumeService(resume_repo, jobseeker_repo)


@pytest.fixture(scope="module")
def jobseeker_ids(test_db, request):
    """
    Insert two job seekers: owner and other.
    Returns (owner_id, other_id, owner_email).
    """
    _, db_file = test_db

    if not _table_exists(db_file, JOBSEEKER_TABLE):
        pytest.skip("job_seekers table not found in schema")

    unique = request.module.__name__.replace(".", "_")

    owner_email = f"{unique}.owner@example.com"
    other_email = f"{unique}.other@example.com"

    owner_id = _insert_minimal_row(
        db_file,
        JOBSEEKER_TABLE,
        preset={
            "email": owner_email,
            "first_name": "Owner",
            "last_name": "User",
            "password_hash": "hash",
        },
    )
    other_id = _insert_minimal_row(
        db_file,
        JOBSEEKER_TABLE,
        preset={
            "email": other_email,
            "first_name": "Other",
            "last_name": "User",
            "password_hash": "hash",
        },
    )

    return owner_id, other_id, owner_email


@pytest.fixture(autouse=True)
def _clean_resume_tables(test_db):
    """
    Keep tests deterministic even if repo/service commits.
    """
    _, db_file = test_db
    if not _table_exists(db_file, RESUMES_TABLE):
        yield
        return

    con = sqlite3.connect(str(db_file))
    try:
        con.execute(f'DELETE FROM "{RESUMES_TABLE}"')
        con.commit()
    finally:
        con.close()

    yield


# -------------------------------
# Tests: list/get/delete/build view
# -------------------------------

def test_list_for_jobseeker_returns_only_own(db_session, resume_service, resume_repo, jobseeker_ids):
    owner_id, other_id, _ = jobseeker_ids

    resume_repo.create(db_session, job_seeker_id=owner_id, raw_text="A", source_id_text="Title A")
    resume_repo.create(db_session, job_seeker_id=owner_id, raw_text="B", source_id_text="Title B")
    resume_repo.create(db_session, job_seeker_id=other_id, raw_text="X", source_id_text="Other")

    rows = resume_service.list_for_jobseeker(db_session, owner_id)
    assert len(rows) == 2
    assert {r.source_id_text for r in rows} == {"Title A", "Title B"}


def test_get_by_id_returns_resume_or_none(db_session, resume_service, resume_repo, jobseeker_ids):
    owner_id, _, _ = jobseeker_ids

    created = resume_repo.create(db_session, job_seeker_id=owner_id, raw_text="Hello", source_id_text="T")
    assert resume_service.get_by_id(db_session, created.id) is not None
    assert resume_service.get_by_id(db_session, 999999999) is None


def test_delete_if_owned_false_if_missing(db_session, resume_service, jobseeker_ids):
    owner_id, _, _ = jobseeker_ids
    assert resume_service.delete_if_owned(db_session, owner_id, 999999999) is False


def test_delete_if_owned_false_if_not_owned(db_session, resume_service, resume_repo, jobseeker_ids):
    owner_id, other_id, _ = jobseeker_ids

    created = resume_repo.create(db_session, job_seeker_id=other_id, raw_text="X", source_id_text="Other")
    assert resume_service.delete_if_owned(db_session, owner_id, created.id) is False


def test_delete_if_owned_true_and_deletes(db_session, resume_service, resume_repo, jobseeker_ids):
    owner_id, _, _ = jobseeker_ids

    created = resume_repo.create(db_session, job_seeker_id=owner_id, raw_text="X", source_id_text="Mine")
    ok = resume_service.delete_if_owned(db_session, owner_id, created.id)

    assert ok is True
    assert resume_service.get_by_id(db_session, created.id) is None


def test_build_resume_text_view_not_found(db_session, resume_service, jobseeker_ids):
    owner_id, _, _ = jobseeker_ids
    result = resume_service.build_resume_text_view(db_session, owner_id, 999999999)
    assert result["status"] == "not_found"


def test_build_resume_text_view_access_denied(db_session, resume_service, resume_repo, jobseeker_ids):
    owner_id, other_id, _ = jobseeker_ids
    created = resume_repo.create(db_session, job_seeker_id=other_id, raw_text="X", source_id_text="Other")

    result = resume_service.build_resume_text_view(db_session, owner_id, created.id)
    assert result["status"] == "access_denied"


def test_build_resume_text_view_ok(db_session, resume_service, resume_repo, jobseeker_ids):
    owner_id, _, owner_email = jobseeker_ids
    created = resume_repo.create(
        db_session,
        job_seeker_id=owner_id,
        raw_text="Resume text here",
        source_id_text="My Title",
    )

    result = resume_service.build_resume_text_view(db_session, owner_id, created.id)

    assert result["status"] == "ok"
    assert result["job_seeker_email"] == owner_email
    assert result["resume_title"] == "My Title"
    assert result["resume_id"] == created.id
    assert result["resume_text"] == "Resume text here"
    assert result["created_at"] is not None


# -------------------------------
# Tests: create_from_upload (mock extractor)
# -------------------------------

@pytest.mark.anyio
async def test_create_from_upload_persists_resume(db_session, resume_service, jobseeker_ids, monkeypatch):
    owner_id, _, _ = jobseeker_ids

    captured = {}

    def fake_extract(filename: str, content_type: str | None, data: bytes) -> str:
        captured["filename"] = filename
        captured["content_type"] = content_type
        captured["data"] = data
        return "EXTRACTED_TEXT"

    monkeypatch.setattr(resume_service_module, "extract_text_from_upload", fake_extract)

    file = FakeUploadFile(
        filename="cv.txt",
        content_type="text/plain",
        data=b"Hello world",
    )

    created = await resume_service.create_from_upload(
        db_session,
        job_seeker_id=owner_id,
        file=file,
        title="My CV Title",
    )

    assert created.id is not None
    assert created.job_seeker_id == owner_id
    assert created.source_id_text == "My CV Title"
    assert created.raw_text == "EXTRACTED_TEXT"

    # Ensure extractor was called with expected data
    assert captured["filename"] == "cv.txt"
    assert captured["content_type"] == "text/plain"
    assert captured["data"] == b"Hello world"

    # Ensure it is stored
    from_db = db_session.get(Resume, created.id)
    assert from_db is not None
    assert from_db.source_id_text == "My CV Title"
    assert from_db.raw_text == "EXTRACTED_TEXT"


@pytest.mark.anyio
async def test_create_from_upload_propagates_extraction_error(db_session, resume_service, jobseeker_ids, monkeypatch):
    owner_id, _, _ = jobseeker_ids

    def fake_extract(*args, **kwargs):
        raise ResumeExtractionError("Unsupported file type")

    monkeypatch.setattr(resume_service_module, "extract_text_from_upload", fake_extract)

    file = FakeUploadFile(
        filename="cv.bad",
        content_type="application/octet-stream",
        data=b"???",
    )

    with pytest.raises(ResumeExtractionError, match="Unsupported"):
        await resume_service.create_from_upload(
            db_session,
            job_seeker_id=owner_id,
            file=file,
            title="Bad",
        )

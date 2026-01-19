# tests/test_job_service.py

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from shared.alembic_runner import upgrade_head
from src.repositories.job_repository import JobRepository
from src.services.job_service import JobService
from src.models import Job


# If your schema uses a different table name for companies, adjust this.
COMPANY_TABLE = "companies"


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
        return "test@example.com"
    if "password" in name or "hash" in name:
        return "test_hash"
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

    Returns: last_insert_rowid() as int.
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

    # Some projects read DATABASE_URL in Alembic env.py, so set it explicitly.
    os.environ["DATABASE_URL"] = db_url

    # Apply migrations (schema for integration tests)
    upgrade_head(db_url)

    yield db_url, db_file

    # Best-effort cleanup on Windows
    try:
        db_file.unlink()
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def engine(test_db):
    """
    Engine without pooling to avoid file locks on Windows.
    """
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
    Provides an isolated Session using a SAVEPOINT pattern.

    Even if the code under test calls session.commit(),
    the outer transaction is rolled back after the test.
    """
    connection = engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False, expire_on_commit=False)
    session = SessionLocal()

    # Start a nested transaction (SAVEPOINT)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        # Restart nested transaction after commit/rollback of the inner one
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def job_repo():
    return JobRepository()


@pytest.fixture()
def job_service(job_repo):
    return JobService(job_repo)


@pytest.fixture(scope="module")
def company_id(test_db, request) -> int:
    """
    Inserts a single company row once per module.
    Uses a unique company_name per module to avoid UNIQUE constraint conflicts.
    """
    _, db_file = test_db

    if not _table_exists(db_file, COMPANY_TABLE):
        return 777

    unique = request.module.__name__.replace(".", "_")
    return _insert_minimal_row(
        db_file,
        COMPANY_TABLE,
        preset={
            "name": f"Test Company {unique}",
            "company_name": f"Test Company {unique}",
            "email": f"{unique}@test.com",
        },
    )


@pytest.fixture(scope="module")
def other_company_id(test_db, request) -> int:
    """
    Creates another company row (for list/filter tests).
    """
    _, db_file = test_db

    # If there is no companies table, just return a different integer.
    if not _table_exists(db_file, COMPANY_TABLE):
        return 888

    unique = request.module.__name__.replace(".", "_")
    return _insert_minimal_row(
        db_file,
        COMPANY_TABLE,
        preset={
            "name": f"Other Company {unique}",
            "company_name": f"Other Company {unique}",
            "email": f"other_{unique}@test.com",
        },
    )


@pytest.fixture(autouse=True)
def _clean_job_related_tables(test_db):
    """
    Ensures test isolation for integration tests.

    Some code paths call session.commit(), which may persist rows beyond
    SAVEPOINT-based test transactions on SQLite. We clean relevant tables
    explicitly to keep tests deterministic.
    """
    _, db_file = test_db

    con = sqlite3.connect(str(db_file))
    try:
        # Delete children first (FK safety), then parent rows.
        con.execute('DELETE FROM "matches"')
        con.execute('DELETE FROM "jobs"')
        con.commit()
    finally:
        con.close()


# -------------------------------
# Positive flow tests (happy path)
# -------------------------------

def test_create_offer_persists_job(db_session, job_service, company_id: int):
    job = job_service.create_offer(
        db_session,
        company_id=company_id,
        title="Junior Python Dev",
        degree="BSc",
        experience="0-1 years",
        required_skills="Python, FastAPI",
        job_text="We need a junior dev",
        skills_weight=1.2,
        degree_weight=0.9,
        experience_weight=1.1,
        weight_general=1.0,
    )

    assert job.id is not None
    assert job.company_id == company_id
    assert "Description:\nWe need a junior dev" in (job.raw_text or "")
    assert job.title == "Junior Python Dev"

    # Verify it is actually stored
    from_db = db_session.get(Job, job.id)
    assert from_db is not None
    assert from_db.company_id == company_id


def test_list_jobs_for_company_returns_only_company_jobs(
    db_session, job_service, company_id: int, other_company_id: int
):
    job_service.create_offer(
        db_session,
        company_id=company_id,
        title="Job A",
        degree="Any",
        experience="Any",
        required_skills="A",
        job_text="A",
    )
    job_service.create_offer(
        db_session,
        company_id=company_id,
        title="Job B",
        degree="Any",
        experience="Any",
        required_skills="B",
        job_text="B",
    )
    job_service.create_offer(
        db_session,
        company_id=other_company_id,
        title="Other",
        degree="Any",
        experience="Any",
        required_skills="X",
        job_text="X",
    )

    jobs = job_service.list_jobs_for_company(db_session, company_id)
    assert len(jobs) == 2
    assert {j.title for j in jobs} == {"Job A", "Job B"}


def test_get_offer_for_company_returns_job(db_session, job_service, company_id: int):
    created = job_service.create_offer(
        db_session,
        company_id=company_id,
        title="Editable",
        degree="Any",
        experience="Any",
        required_skills="X",
        job_text="Hello",
    )

    fetched = job_service.get_offer_for_company(db_session, company_id=company_id, job_id=created.id)
    assert fetched.id == created.id
    assert fetched.company_id == company_id


def test_update_offer_updates_fields_and_raw_text(db_session, job_service, company_id: int):
    created = job_service.create_offer(
        db_session,
        company_id=company_id,
        title="Old title",
        degree="Old degree",
        experience="Old exp",
        required_skills="Old skills",
        job_text="Old text",
        skills_weight=1.0,
    )

    updated = job_service.update_offer(
        db_session,
        company_id=company_id,
        job_id=created.id,
        title="New title",
        job_text="New description",
        skills_weight=2.5,
    )

    assert updated.title == "New title"
    assert updated.skills_weight == 2.5
    assert "Title: New title" in (updated.raw_text or "")
    assert "Description:\nNew description" in (updated.raw_text or "")

    # Verify persisted
    from_db = db_session.get(Job, created.id)
    assert from_db is not None
    assert from_db.title == "New title"


def test_delete_offer_removes_job(db_session, job_service, company_id: int):
    created = job_service.create_offer(
        db_session,
        company_id=company_id,
        title="To delete",
        degree="Any",
        experience="Any",
        required_skills="X",
        job_text="X",
    )
    job_id = created.id

    job_service.delete_offer(db_session, company_id=company_id, job_id=job_id)

    from_db = db_session.get(Job, job_id)
    assert from_db is None


# -------------------------------
# Negative flow tests (error path)
# -------------------------------

def test_get_offer_for_company_raises_value_error_if_missing(db_session, job_service, company_id: int):
    with pytest.raises(ValueError, match="Job offer not found"):
        job_service.get_offer_for_company(db_session, company_id=company_id, job_id=999999999)


def test_get_offer_for_company_raises_permission_error_if_wrong_company(db_session, job_service, company_id: int):
    created = job_service.create_offer(
        db_session,
        company_id=company_id,
        title="Private",
        degree="Any",
        experience="Any",
        required_skills="X",
        job_text="X",
    )

    with pytest.raises(PermissionError, match="does not belong"):
        job_service.get_offer_for_company(db_session, company_id=company_id + 1, job_id=created.id)


def test_update_offer_raises_value_error_if_missing(db_session, job_service, company_id: int):
    with pytest.raises(ValueError, match="Job offer not found"):
        job_service.update_offer(db_session, company_id=company_id, job_id=123456789, title="X")


def test_delete_offer_raises_value_error_if_missing(db_session, job_service, company_id: int):
    with pytest.raises(ValueError, match="Job offer not found"):
        job_service.delete_offer(db_session, company_id=company_id, job_id=123456789)

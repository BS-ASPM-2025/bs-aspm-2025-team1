# tests/services/test_jobseeker_auth_service.py

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from shared.alembic_runner import upgrade_head
from src.repositories.jobseeker_repository import JobSeekerRepository
from src.security.auth.jobseeker_auth_service import JobSeekerAuthService
from src.models import JobSeeker


JOBSEEKER_TABLE = "job_seekers"


# -------------------------------
# Password hashing helper
# -------------------------------

def _hash_password(raw: str) -> str:
    """
    Prefer project hashing function if available.
    Fallback to passlib CryptContext for bcrypt.
    """
    try:
        from src.security.passwords import hash_password  # if exists in your project
        return hash_password(raw)
    except Exception:
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.hash(raw)


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
def jobseeker_repo():
    return JobSeekerRepository()


@pytest.fixture()
def jobseeker_auth_service(jobseeker_repo):
    return JobSeekerAuthService(jobseeker_repo)


@pytest.fixture(scope="module")
def jobseeker_row(test_db, request):
    """
    Inserts a single job seeker with known password_hash.
    Returns (jobseeker_id, email, raw_password).
    """
    _, db_file = test_db

    if not _table_exists(db_file, JOBSEEKER_TABLE):
        pytest.skip("job_seekers table not found in test DB schema")

    unique = request.module.__name__.replace(".", "_")
    raw_password = "Secret123!"
    email = f"{unique}@example.com"

    password_hash = _hash_password(raw_password)

    jobseeker_id = _insert_minimal_row(
        db_file,
        JOBSEEKER_TABLE,
        preset={
            "email": email,
            "password_hash": password_hash,
            # these are common columns; if your schema differs, PRAGMA introspection fills the rest
            "first_name": "Test",
            "last_name": "User",
        },
    )

    return jobseeker_id, email, raw_password


# -------------------------------
# Tests
# -------------------------------

def test_authenticate_returns_jobseeker_on_valid_credentials(db_session, jobseeker_auth_service, jobseeker_row):
    jobseeker_id, email, raw_password = jobseeker_row

    jobseeker = jobseeker_auth_service.authenticate(db_session, email, raw_password)

    assert jobseeker is not None
    assert isinstance(jobseeker, JobSeeker)
    assert jobseeker.id == jobseeker_id
    assert jobseeker.email == email


def test_authenticate_returns_none_if_email_missing(db_session, jobseeker_auth_service, jobseeker_row):
    _, _, raw_password = jobseeker_row

    jobseeker = jobseeker_auth_service.authenticate(db_session, "no-such-user@example.com", raw_password)

    assert jobseeker is None


def test_authenticate_returns_none_on_wrong_password(db_session, jobseeker_auth_service, jobseeker_row):
    _, email, _ = jobseeker_row

    jobseeker = jobseeker_auth_service.authenticate(db_session, email, "wrong-password")

    assert jobseeker is None

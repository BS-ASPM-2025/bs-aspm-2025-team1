# tests/services/test_company_auth_service.py

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from shared.alembic_runner import upgrade_head
from src.repositories.company_repository import CompanyRepository
from src.security.auth.company_auth_service import CompanyAuthService
from src.models import Company


COMPANY_TABLE = "companies"


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
def company_repo():
    return CompanyRepository()


@pytest.fixture()
def company_auth_service(company_repo):
    return CompanyAuthService(company_repo)


@pytest.fixture(scope="module")
def company_row(test_db, request):
    """
    Inserts a single company with known password_hash.
    Returns (company_id, company_name, raw_password).
    """
    _, db_file = test_db

    if not _table_exists(db_file, COMPANY_TABLE):
        pytest.skip("companies table not found in test DB schema")

    unique = request.module.__name__.replace(".", "_")
    raw_password = "Secret123!"

    company_name = f"Test Company {unique}"
    password_hash = _hash_password(raw_password)

    company_id = _insert_minimal_row(
        db_file,
        COMPANY_TABLE,
        preset={
            # Depending on your schema, one of these may be used by repo:
            "company_name": company_name,
            "name": company_name,
            "email": f"{unique}@test.com",
            "password_hash": password_hash,
        },
    )

    return company_id, company_name, raw_password


# -------------------------------
# Tests
# -------------------------------

def test_authenticate_returns_company_on_valid_credentials(db_session, company_auth_service, company_row):
    company_id, company_name, raw_password = company_row

    company = company_auth_service.authenticate(db_session, company_name, raw_password)

    assert company is not None
    assert isinstance(company, Company)
    assert company.id == company_id


def test_authenticate_returns_none_if_company_missing(db_session, company_auth_service, company_row):
    _, _, raw_password = company_row

    company = company_auth_service.authenticate(db_session, "No Such Company", raw_password)

    assert company is None


def test_authenticate_returns_none_on_wrong_password(db_session, company_auth_service, company_row):
    _, company_name, _ = company_row

    company = company_auth_service.authenticate(db_session, company_name, "wrong-password")

    assert company is None

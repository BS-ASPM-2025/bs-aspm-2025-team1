
import os
import sqlite3
import base64
import json
import pytest
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional

from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from starlette.middleware.sessions import SessionMiddleware



import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
import app as app_module
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared import Base, get_db
from app import app


# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_shared.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def _force_project_root_cwd():
    # move cwd to project root (one level above tests/)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(root)

# Override dependency
def override_get_db():
    """
    Dependency override to provide a database session for testing.
    Yields:
        db: SQLAlchemy Session connected to the test database

    """

from itsdangerous import TimestampSigner

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from shared import get_db
from shared.alembic_runner import upgrade_head

import json
from base64 import b64encode



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
        return "Test User"
    return "test"


def _insert_minimal_row(db_file: Path, table: str, preset: dict | None = None) -> int:
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


def _find_dependency_for_route(app, path: str, method: str) -> Optional[Callable]:
    method = method.upper()
    for r in app.router.routes:
        if isinstance(r, APIRoute) and r.path == path and method in (r.methods or set()):
            deps = [d.call for d in (r.dependant.dependencies or []) if d.call]

            # 1) точечный поиск: имя/модуль содержит job+seeker
            for call in deps:
                n = (getattr(call, "__name__", "") or "").lower()
                m = (getattr(call, "__module__", "") or "").lower()
                if "job" in n and "seeker" in n:
                    return call
                if "job" in m and "seeker" in m:
                    return call

            # 2) fallback: любая dependency, кроме get_db
            for call in deps:
                if call is not get_db:
                    return call
    return None



def _get_session_middleware_config(app):
    for mw in app.user_middleware:
        if mw.cls is SessionMiddleware:
            # Starlette хранит параметры в kwargs (options уже нет)
            opts = getattr(mw, "kwargs", None) or getattr(mw, "options", None) or {}
            secret_key = opts.get("secret_key")
            cookie_name = opts.get("session_cookie", "session")
            return secret_key, cookie_name

    raise RuntimeError("SessionMiddleware not found in app.user_middleware")



def _make_session_cookie(secret_key: str, session_dict: dict) -> str:
    signer = TimestampSigner(secret_key)
    data = base64.b64encode(json.dumps(session_dict).encode("utf-8"))
    return signer.sign(data).decode("utf-8")


@pytest.fixture(scope="module")
def client(tmp_path_factory, request):
    safe_name = request.module.__name__.replace(".", "_")
    db_dir = tmp_path_factory.mktemp("db")
    db_file = db_dir / f"{safe_name}.db"

    test_db_url = f"sqlite:///{db_file.as_posix()}"
    os.environ["DATABASE_URL"] = test_db_url

    # импорт после env
    from app import app  # noqa

    # миграции
    upgrade_head(test_db_url)

    # engine без пула, чтобы не держать файл залоченным
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=False,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        c.test_db_url = test_db_url
        c.test_db_file = db_file
        yield c
    Base.metadata.drop_all(bind=engine)

#--------------------------------------------------------------------

def _init_jobs_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_text TEXT,
        id_text TEXT,
        title TEXT,
        company TEXT,
        required_skills TEXT,
        degree TEXT,
        experience TEXT,
        skills_weight FLOAT,
        degree_weight FLOAT
    );
    """)
    conn.commit()


@pytest.fixture()
def client(tmp_path):
    # Create a temporary SQLite DB file for the test
    db_path = tmp_path / "test_my_database.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_jobs_schema(conn)
    conn.close()

    # Override the dependency so the route uses the temp DB
    def override_get_sqlite_conn():
        c = sqlite3.connect(str(db_path), check_same_thread=False)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    app_module.app.dependency_overrides[app_module.get_sqlite_conn] = override_get_sqlite_conn

    with TestClient(app_module.app) as test_client:
        yield test_client

    app_module.app.dependency_overrides.clear()


@pytest.fixture()
def db_path(tmp_path):
    # If you want direct DB access in tests, reuse same tmp_path logic per-test
    return tmp_path / "test_my_database.db"

    # teardown
    app.dependency_overrides.clear()
    engine.dispose()

    try:
        db_file.unlink()
    except PermissionError:
        pass


@pytest.fixture(scope="module")
def job_seeker_id(client) -> int:
    return _insert_minimal_row(
        client.test_db_file,
        "job_seekers",
        preset={
            "full_name": "Test JobSeeker",
            "name": "Test JobSeeker",
            "email": "jobseeker@test.com",
        },
    )


@pytest.fixture(scope="function")
def auth_job_seeker(client, job_seeker_id):

    #Делает job seeker "авторизованным" для upload_resume:
    #- либо override Depends() у POST /upload_resume
    #- либо ставит signed session cookie (если endpoint читает request.session напрямую)

    app = client.app

    dep = _find_dependency_for_route(app, "/upload_resume", "POST")
    if dep is not None:
        app.dependency_overrides[dep] = lambda: job_seeker_id
        yield
        app.dependency_overrides.pop(dep, None)
        return

    # fallback: cookie
    secret_key, cookie_name = _get_session_middleware_config(app)
    if not secret_key:
        pytest.skip(
            "Не нашёл dependency на POST /upload_resume и не нашёл SessionMiddleware secret_key. "
            "Нужно понять, как именно endpoint проверяет job seeker session."
        )

    # ВАЖНО: ключ должен совпасть с тем, что читает приложение
    cookie_val = _make_session_cookie(secret_key, {"job_seeker_id": job_seeker_id})
    client.cookies.set(cookie_name, cookie_val)

    yield

    try:
        del client.cookies[cookie_name]
    except KeyError:
        pass

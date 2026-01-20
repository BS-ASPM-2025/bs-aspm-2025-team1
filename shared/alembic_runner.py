import os
import sqlite3
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.script import ScriptDirectory
from alembic.config import Config
from filelock import FileLock


def _sqlite_db_file_from_url(root: Path, url: str) -> Optional[Path]:
    if not url.startswith("sqlite:///"):
        return None

    rel = url[len("sqlite:///"):]  # "./file.db" or "D:/abs/file.db"
    p = Path(rel)
    if not p.is_absolute():
        p = (root / p).resolve()
    return p


def _dump_sqlite_state(db_file: Path) -> None:
    if not db_file.exists():
        print(f"[alembic_runner] sqlite file does NOT exist yet: {db_file}")
        return

    conn = sqlite3.connect(str(db_file))
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        print(f"[alembic_runner] sqlite tables: {tables}")

        if "alembic_version" in tables:
            ver = conn.execute("SELECT version_num FROM alembic_version").fetchone()
            print(f"[alembic_runner] alembic_version: {ver[0] if ver else None}")
        else:
            print("[alembic_runner] alembic_version table is MISSING")
    finally:
        conn.close()


def upgrade_head(db_url: str | None = None) -> None:
    root = Path(__file__).resolve().parents[1]  # repo root

    cfg = Config(str(root / "alembic.ini"))

    # ВАЖНО: фиксируем script_location абсолютным путём, чтобы исключить “не видит versions”
    cfg.set_main_option("script_location", str(root / "alembic"))

    url = db_url or os.getenv("DATABASE_URL", "sqlite:///./my_database.db")

    db_file = _sqlite_db_file_from_url(root, url)
    if db_file:
        # Делаем URL абсолютным (на Windows это критично для предсказуемости)
        url = f"sqlite:///{db_file.as_posix()}"
        lock_path = db_file.with_suffix(db_file.suffix + ".migrate.lock")
    else:
        lock_path = root / "db.migrate.lock"

    cfg.set_main_option("sqlalchemy.url", url)

    print(f"[alembic_runner] url={url}")
    if db_file:
        print(f"[alembic_runner] resolved sqlite file={db_file}")
        _dump_sqlite_state(db_file)

    print(f"[alembic_runner] trying lock: {lock_path}")
    with FileLock(str(lock_path), timeout=30):
        print("[alembic_runner] lock acquired, running alembic upgrade head ...")
        script = ScriptDirectory.from_config(cfg)
        print(f"[alembic_runner] script_location={cfg.get_main_option('script_location')}")
        print(f"[alembic_runner] heads={script.get_heads()}")
        print(f"[alembic_runner] all_revisions={[rev.revision for rev in script.walk_revisions()]}")
        command.upgrade(cfg, "head")
        print("[alembic_runner] alembic upgrade finished")

    if db_file:
        _dump_sqlite_state(db_file)

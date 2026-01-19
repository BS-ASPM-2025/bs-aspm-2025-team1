"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-17
"""
from alembic import op
from pathlib import Path

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _read_sql(rel_path: str) -> str:
    root = Path(__file__).resolve().parents[2]  # repo root
    return (root / rel_path).read_text(encoding="utf-8")


def _exec_sql(sql: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        raw = bind.connection.connection  # sqlite3 connection
        raw.executescript(sql)
    else:
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            bind.exec_driver_sql(stmt)


def upgrade() -> None:
    _exec_sql(_read_sql("db/migrations/V0001__initial_schema.sql"))


def downgrade() -> None:
    _exec_sql("""
    DROP TABLE IF EXISTS matches;
    DROP TABLE IF EXISTS resumes;
    DROP TABLE IF EXISTS jobs;
    DROP TABLE IF EXISTS job_seekers;
    DROP TABLE IF EXISTS companies;
    """)


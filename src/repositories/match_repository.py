from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from src.models import Match


class MatchRepository:
    def delete_by_job_id(self, db: Session, job_id: int) -> None:
        stmt = delete(Match).where(Match.job_id == int(job_id))
        db.execute(stmt)
        db.commit()

    def bulk_create(self, db: Session, matches: Iterable[Match]) -> None:
        db.add_all(list(matches))
        db.commit()

    def list_by_job_id(self, db: Session, job_id: int, limit: Optional[int] = None) -> list[Match]:
        stmt = (
            select(Match)
            .where(Match.job_id == int(job_id))
            .order_by(desc(Match.score), desc(Match.created_at))
        )
        if limit is not None:
            stmt = stmt.limit(int(limit))
        return list(db.scalars(stmt).all())

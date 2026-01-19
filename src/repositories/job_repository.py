from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from src.models import Job

class JobRepository:
    def create(self, db: Session, job: Job) -> Job:
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def find_by_company_id(self, db: Session, company_id: int) -> List[Job]:
        stmt = (
            select(Job)
            .where(Job.company_id == int(company_id))
            .order_by(desc(Job.created_at))
        )
        return list(db.scalars(stmt).all())

    def get_by_id(self, db: Session, job_id: int) -> Optional[Job]:
        return db.query(Job).filter(Job.id == int(job_id)).one_or_none()

    def delete(self, db: Session, job: Job) -> None:
        db.delete(job)
        db.commit()

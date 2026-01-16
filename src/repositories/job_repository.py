from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from models import Job

class JobRepository:
    def create(self, db: Session, job: Job) -> Job:
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def find_by_company_name(self, db: Session, company_name: str) -> List[Job]:
        stmt = (
            select(Job)
            .where(Job.company == company_name)
            .order_by(desc(Job.created_at))
        )
        return list(db.scalars(stmt).all())

    def get_by_id(self, db: Session, job_id: int) -> Optional[Job]:
        return db.query(Job).filter(Job.id == int(job_id)).one_or_none()

    def delete(self, db: Session, job: Job) -> None:
        db.delete(job)
        db.commit()
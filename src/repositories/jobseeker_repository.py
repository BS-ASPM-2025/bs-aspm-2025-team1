from sqlalchemy.orm import Session

from src.models import JobSeeker


class JobSeekerRepository:
    def get_by_email(self, db: Session, email: str) -> JobSeeker | None:
        return db.query(JobSeeker).filter(JobSeeker.email == email).one_or_none()

    def get_by_id(self, db: Session, jobseeker_id: int) -> JobSeeker | None:
        return db.query(JobSeeker).filter(JobSeeker.id == int(jobseeker_id)).one_or_none()

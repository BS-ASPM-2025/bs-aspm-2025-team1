from sqlalchemy.orm import Session

from src.models import JobSeeker
from src.repositories.jobseeker_repository import JobSeekerRepository
from src.security.passwords import verify_password


class JobSeekerAuthService:
    def __init__(self, jobseeker_repo: JobSeekerRepository):
        self.jobseeker_repo = jobseeker_repo

    def authenticate(self, db: Session, email: str, raw_password: str) -> JobSeeker | None:
        jobseeker = self.jobseeker_repo.get_by_email(db, email)
        if jobseeker is None:
            return None

        if not verify_password(raw_password, jobseeker.password_hash):
            return None

        return jobseeker

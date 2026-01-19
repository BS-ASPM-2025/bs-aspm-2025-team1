from sqlalchemy.orm import Session
from fastapi import UploadFile

from src.models import Resume
from src.repositories.resume_repository import ResumeRepository
from src.repositories.jobseeker_repository import JobSeekerRepository
from src.tools.resume_text_extractor import (
    extract_text_from_upload,
    read_upload_bytes,
    ResumeExtractionError,
)


class ResumeService:
    def __init__(self, resume_repo: ResumeRepository, jobseeker_repo: JobSeekerRepository):
        self.resume_repo = resume_repo
        self.jobseeker_repo = jobseeker_repo

    def list_for_jobseeker(self, db: Session, job_seeker_id: int) -> list[Resume]:
        return self.resume_repo.list_by_job_seeker_id(db, job_seeker_id)

    def get_by_id(self, db: Session, resume_id: int) -> Resume | None:
        return self.resume_repo.get_by_id(db, resume_id)

    async def create_from_upload(
        self,
        db: Session,
        job_seeker_id: int,
        file: UploadFile,
        title: str,
    ) -> Resume:
        data = await read_upload_bytes(file)
        text = extract_text_from_upload(file.filename or "", file.content_type, data)

        return self.resume_repo.create(
            db=db,
            job_seeker_id=job_seeker_id,
            raw_text=text,
            source_id_text=title,
        )

    def delete_if_owned(self, db: Session, job_seeker_id: int, resume_id: int) -> bool:
        resume = self.resume_repo.get_by_id(db, resume_id)
        if resume is None:
            return False

        if int(resume.job_seeker_id) != int(job_seeker_id):
            return False

        self.resume_repo.delete(db, resume)
        return True

    def build_resume_text_view(self, db: Session, session_job_seeker_id: int, resume_id: int) -> dict:
        resume = self.resume_repo.get_by_id(db, resume_id)
        if resume is None:
            return {"status": "not_found"}

        if int(resume.job_seeker_id) != int(session_job_seeker_id):
            return {"status": "access_denied"}

        js = self.jobseeker_repo.get_by_id(db, session_job_seeker_id)
        job_seeker_email = js.email if js else f"jobseeker_id={session_job_seeker_id}"

        return {
            "status": "ok",
            "job_seeker_email": job_seeker_email,
            "resume_title": resume.source_id_text or f"Resume #{resume.id}",
            "resume_id": resume.id,
            "created_at": resume.created_at,
            "resume_text": resume.raw_text or "",
        }

from typing import List, Optional
from sqlalchemy.orm import Session

from src.models import Job
from src.repositories.job_repository import JobRepository

class JobService:
    def __init__(self, job_repo: JobRepository):
        self._job_repo = job_repo

    def create_offer(
        self,
        db: Session,
        *,
        company_id: int,
        title: str,
        degree: str,
        experience: str,
        required_skills: str,
        job_text: str,
        skills_weight: float = 1.0,
        degree_weight: float = 1.0,
        experience_weight: float = 1.0,
        weight_general: float = 1.0,
    ) -> Job:
        combined_text = (
            f"Title: {title}\n"
            f"Skills: {required_skills}\n"
            f"Degree: {degree}\n"
            f"Experience: {experience}\n\n"
            f"Description:\n{job_text}"
        )

        new_job = Job(
            company_id=int(company_id),
            raw_text=combined_text,
            title=title,
            required_skills=required_skills,
            degree=degree,
            experience=experience,
            skills_weight=float(skills_weight),
            degree_weight=float(degree_weight),
            experience_weight=float(experience_weight),
            weight_general=float(weight_general),
        )
        return self._job_repo.create(db, new_job)

    def list_jobs_for_company(self, db: Session, company_id: int) -> List[Job]:
        return self._job_repo.find_by_company_id(db, company_id)

    def get_offer_for_company(self, db: Session, *, company_id: int, job_id: int) -> Job:
        job = self._job_repo.get_by_id(db, job_id)
        if not job:
            raise ValueError("Job offer not found")
        if int(job.company_id) != int(company_id):
            raise PermissionError("Job offer does not belong to this company")
        return job

    def update_offer(
        self,
        db: Session,
        *,
        company_id: int,
        job_id: int,
        title: Optional[str] = None,
        degree: Optional[str] = None,
        experience: Optional[str] = None,
        required_skills: Optional[str] = None,
        job_text: Optional[str] = None,
        skills_weight: Optional[float] = None,
        degree_weight: Optional[float] = None,
        experience_weight: Optional[float] = None,
        weight_general: Optional[float] = None,
    ) -> Job:
        job = self.get_offer_for_company(db, company_id=company_id, job_id=job_id)

        if title is not None:
            job.title = title
        if degree is not None:
            job.degree = degree
        if experience is not None:
            job.experience = experience
        if required_skills is not None:
            job.required_skills = required_skills

        if skills_weight is not None:
            job.skills_weight = float(skills_weight)
        if degree_weight is not None:
            job.degree_weight = float(degree_weight)
        if experience_weight is not None:
            job.experience_weight = float(experience_weight)
        if weight_general is not None:
            job.weight_general = float(weight_general)

        if job_text is not None:
            combined_text = (
                f"Title: {job.title or ''}\n"
                f"Skills: {job.required_skills or ''}\n"
                f"Degree: {job.degree or ''}\n"
                f"Experience: {job.experience or ''}\n\n"
                f"Description:\n{job_text}"
            )
            job.raw_text = combined_text

        db.commit()
        db.refresh(job)
        return job

    def delete_offer(self, db: Session, *, company_id: int, job_id: int) -> None:
        job = self.get_offer_for_company(db, company_id=company_id, job_id=job_id)
        self._job_repo.delete(db, job)

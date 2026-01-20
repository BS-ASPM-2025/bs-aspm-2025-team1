import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from models import Job
from src.repositories.company_repository import CompanyRepository
from src.repositories.job_repository import JobRepository


class JobService:
    def __init__(self, _job_repo: JobRepository, _company_repo: CompanyRepository):
        self._job_repo = _job_repo
        self._company_repo = _company_repo


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
        company_name = self._company_repo.get_name_by_id(db, company_id)
        if not company_name:
            raise ValueError(f"Company with id={company_id} not found")

        combined_text = (
            f"Title: {title}\n"
            f"Skills: {required_skills}\n"
            f"Degree: {degree}\n"
            f"Experience: {experience}\n\n"
            f"Description:\n{job_text}"
        )

        new_job = Job(
            id_text=str(uuid.uuid4()),
            job_text=combined_text,
            title=title,
            company=company_name,
            required_skills=required_skills,
            degree=degree,
            experience=experience,
            skills_weight=float(skills_weight),
            degree_weight=float(degree_weight),
            experience_weight=float(experience_weight),
            weight_general=float(weight_general),
        )

        return self._job_repo.create(db, new_job)

    def get_offer_for_company(self, db: Session, *, company_id: int, job_id: int) -> Job:
        job = self._job_repo.get_by_id(db, job_id)
        if not job:
            raise ValueError("Job offer not found")

        company_name = self._company_repo.get_name_by_id(db, company_id)
        if not company_name:
            raise ValueError("Company not found")

        if (job.company or "").strip() != company_name.strip():
            raise PermissionError("Job offer does not belong to this company")

        return job


    def list_job_summaries_for_company(self, db: Session, company_id: int) -> List[Dict[str, Any]]:
        company_name = self._company_repo.get_name_by_id(db, company_id)
        if not company_name:
            return []

        jobs = self._job_repo.find_by_company_name(db, company_name)

        return [
            {
                "id": j.id,
                "title": j.title or "(untitled)",
                "created_at": j.created_at,
            }
            for j in jobs
        ]


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
        job = self._job_repo.get_by_id(db, job_id)
        # Security layer
        if not job:
            raise ValueError("Job offer not found")

        company_name = self._company_repo.get_name_by_id(db, company_id)
        if not company_name:
            raise ValueError("Company not found")

        if job.company != company_name:
            raise ValueError("Job offer does not belong to this company")

        # Update layer
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
            job.job_text = combined_text

        db.commit()
        db.refresh(job)
        return job

    def delete_offer(self, db: Session, *, company_id: int, job_id: int) -> None:
        job = self._job_repo.get_by_id(db, job_id)
        if not job:
            raise ValueError("Job offer does not exist")

        company_name = self._company_repo.get_name_by_id(db, company_id)
        if not company_name:
            raise ValueError("Company does not exist")

        if (job.company or "").strip() != company_name.strip():
            raise PermissionError("Job offer does not belong to this company")

        self._job_repo.delete(db, job)
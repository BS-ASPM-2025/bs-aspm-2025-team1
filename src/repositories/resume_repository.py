from sqlalchemy.orm import Session

from src.models import Resume


class ResumeRepository:
    def create(
        self,
        db: Session,
        job_seeker_id: int,
        raw_text: str,
        source_id_text: str | None = None,
    ) -> Resume:
        resume = Resume(
            job_seeker_id=int(job_seeker_id),
            raw_text=raw_text,
            source_id_text=source_id_text,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume

    def get_by_id(self, db: Session, resume_id: int) -> Resume | None:
        return db.query(Resume).filter(Resume.id == int(resume_id)).one_or_none()

    def list_by_job_seeker_id(self, db: Session, job_seeker_id: int) -> list[Resume]:
        return (
            db.query(Resume)
            .filter(Resume.job_seeker_id == int(job_seeker_id))
            .order_by(Resume.created_at.desc())
            .all()
        )

    def delete(self, db: Session, resume: Resume) -> None:
        db.delete(resume)
        db.commit()
